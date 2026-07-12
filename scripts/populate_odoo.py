"""
populate_odoo.py
Carga los CSVs sintéticos (scripts/odoo_synthetic_data/) en Odoo vía XML-RPC.
Se ejecuta dentro del contenedor `web`, tras el arranque de Odoo.

El addon gym_backoffice solo depende de base/contacts/mail, así que únicamente
existen modelos para centros, socios (res.partner), accesos y health score.
Los CSVs que no tienen modelo Odoo equivalente (crm_leads, facturacion,
helpdesk_tickets, empleados_entrenadores, ventas_servicios, inventario,
mantenimiento, marketing_automation, encuestas_satisfaccion,
eventos_participacion, engagement.csv, suscripciones.csv) se omiten
explícitamente: importarlos exigiría instalar crm/helpdesk/sale/hr o crear
modelos nuevos, lo cual no corresponde a este script.
"""

import csv
import os
import time
import xmlrpc.client
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path("data")

# Por defecto "localhost": funciona cuando este script corre dentro del mismo
# contenedor que Odoo (ver docker-compose.yml de la raíz). Si se ejecuta desde
# un contenedor separado (ver .devcontainer/docker-compose.yml, servicio
# "populate"), hay que apuntar al hostname del servicio de Odoo vía ODOO_HOST.
ODOO_HOST = os.environ.get("ODOO_HOST", "localhost")
URL = f"http://{ODOO_HOST}:8069"
DB = "mydb"
USERNAME = "admin"
PASSWORD = "admin"

SKIPPED_CSVS = [
    "crm_leads.csv",
    "facturacion.csv",
    "helpdesk_tickets.csv",
    "empleados_entrenadores.csv",
    "ventas_servicios.csv",
    "inventario.csv",
    "mantenimiento.csv",
    "marketing_automation.csv",
    "encuestas_satisfaccion.csv",
    "eventos_participacion.csv",
    "engagement.csv",
    "suscripciones.csv",
]

print("Conectando a Odoo...")
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = None
for attempt in range(30):
    try:
        uid = common.authenticate(DB, USERNAME, PASSWORD, {})
        if uid:
            print(f"Autenticado como uid={uid}")
            break
    except Exception as e:
        print(f"Intento {attempt + 1}/30 fallido: {e}")
    time.sleep(10)

if not uid:
    raise SystemExit("No se pudo autenticar con Odoo después de 30 intentos.")

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")


def execute(model, method, args=None, kwargs=None):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args or [], kwargs or {})


def read_csv(name):
    with open(DATA_DIR / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def as_bool(v):
    return str(v).strip().lower() == "true"


def as_float(v, default=0.0):
    v = (v or "").strip()
    return float(v) if v else default


def as_int(v, default=0):
    v = (v or "").strip()
    return int(float(v)) if v else default


for name in SKIPPED_CSVS:
    print(
        f"Omitido {name}: no hay modelo Odoo instalado que lo soporte "
        f"(gym_backoffice solo depende de base/contacts/mail)."
    )

# --- Centros deportivos -> gym.center ---
print("Creando centros deportivos...")
centros = read_csv("centros_deportivos.csv")
center_ids = {}
for c in centros:
    existing = execute(
        "gym.center",
        "search_read",
        [[["name", "=", c["nombre"]]]],
        {"fields": ["id"], "limit": 1},
    )
    if existing:
        center_ids[c["id"]] = existing[0]["id"]
        continue
    vals = {
        "name": c["nombre"],
        "city": c["ciudad"],
        "capacity": as_int(c["aforo_maximo"]),
    }
    cid = execute("gym.center", "create", [vals])
    center_ids[c["id"]] = cid
print(f"  {len(center_ids)} centros creados/existentes")

# --- Contactos -> res.partner (socios) ---
print("Creando socios (res.partner)...")
contactos = read_csv("contactos.csv")

MEMBERSHIP_TYPE_MAP = {
    "Básico": "basic",
    "Estándar": "basic",
    "Premium": "premium",
    "VIP": "vip",
}

partner_ids = {}
BATCH = 200
buffer_refs, buffer_vals = [], []


def flush_partners():
    if not buffer_vals:
        return
    ids = execute("res.partner", "create", [buffer_vals])
    for ref, pid in zip(buffer_refs, ids):
        partner_ids[ref] = pid
    buffer_refs.clear()
    buffer_vals.clear()


for row in contactos:
    ref = f"gym_cliente_{row['id']}"
    existing = execute(
        "res.partner",
        "search_read",
        [[["ref", "=", ref]]],
        {"fields": ["id"], "limit": 1},
    )
    if existing:
        partner_ids[row["id"]] = existing[0]["id"]
        continue

    estado = row["estado"]
    member_status = "churned" if estado == "Baja" else "active"

    vals = {
        "name": f"{row['nombre']} {row['apellidos']}".strip(),
        "ref": ref,
        "city": row["ciudad"],
        "zip": row["codigo_postal"],
        "is_gym_member": True,
        "gym_center_id": center_ids.get(row["centro_id"]),
        "membership_type": MEMBERSHIP_TYPE_MAP.get(row["segmento"], "basic"),
        "membership_start": row["fecha_alta"] or None,
        "member_status": member_status,
    }
    buffer_refs.append(row["id"])
    buffer_vals.append(vals)
    if len(buffer_vals) >= BATCH:
        flush_partners()

flush_partners()
print(f"  {len(partner_ids)} socios creados/existentes")

# --- Registro de accesos -> gym.access ---
print("Creando registros de acceso (esto puede tardar)...")
accesos = read_csv("registro_accesos.csv")

created_access = 0
skipped_access = 0
buffer = []


def flush_access():
    global created_access
    if not buffer:
        return
    execute("gym.access", "create", [list(buffer)])
    created_access += len(buffer)
    buffer.clear()


for row in accesos:
    partner_id = partner_ids.get(row["cliente_id"])
    center_id = center_ids.get(row["centro_id"])
    if not partner_id:
        skipped_access += 1
        continue

    check_in = f"{row['fecha']} {row['hora']}:00"
    try:
        check_in_dt = datetime.strptime(check_in, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        skipped_access += 1
        continue

    duration_min = as_int(row["duracion_entrenamiento_min"])
    check_out_dt = (
        check_in_dt + timedelta(minutes=duration_min) if duration_min else None
    )

    vals = {
        "partner_id": partner_id,
        "gym_center_id": center_id,
        "check_in": check_in_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "activity_type": "class" if row["clase_asistida"] else "gym_floor",
    }
    if check_out_dt:
        vals["check_out"] = check_out_dt.strftime("%Y-%m-%d %H:%M:%S")

    buffer.append(vals)
    if len(buffer) >= 1000:
        flush_access()
        print(f"  {created_access} accesos creados...")

flush_access()
print(
    f"  {created_access} accesos creados, {skipped_access} omitidos (socio no encontrado)"
)

# --- Actividad + customer_health -> gym.customer.health ---
print("Creando health scores (gym.customer.health)...")
actividad = {r["cliente_id"]: r for r in read_csv("actividad_deportiva.csv")}
health = {r["cliente_id"]: r for r in read_csv("customer_health.csv")}

RISK_MAP = {"bajo": "low", "medio": "medium", "alto": "high"}

created_health = 0
buffer = []


def flush_health():
    global created_health
    if not buffer:
        return
    execute("gym.customer.health", "create", [list(buffer)])
    created_health += len(buffer)
    buffer.clear()


for cliente_id, partner_id in partner_ids.items():
    act = actividad.get(cliente_id)
    hlt = health.get(cliente_id)
    if not act and not hlt:
        continue

    vals = {"partner_id": partner_id}
    if hlt:
        vals["date"] = hlt["fecha_ultima_prediccion"] or None
        vals["churn_probability"] = as_float(hlt["riesgo_churn_pct"]) / 100.0
        vals["churn_risk"] = RISK_MAP.get(hlt["nivel_riesgo"].strip().lower(), None)
        notes = hlt.get("explicacion_ia")
        if notes:
            vals["notes"] = notes
    if act:
        vals["visits_last_30_days"] = as_int(act["visitas_ultimos_30_dias"])
        vals["visits_last_90_days"] = as_int(act["visitas_ultimos_90_dias"])
        vals["days_since_last_visit"] = as_int(act["dias_desde_ultima_visita"])
        v30 = vals["visits_last_30_days"]
        vals["avg_weekly_visits"] = v30 / 4.0

    buffer.append(vals)
    if len(buffer) >= 500:
        flush_health()

flush_health()
print(f"  {created_health} health scores creados")

print("Populate complete!")
print("Ahora ve a Gimnasio → Entrenar Modelo de Churn en el backend de Odoo.")
