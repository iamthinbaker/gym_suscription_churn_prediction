#!/usr/bin/env python3
"""
Generador de datos sintéticos para predicción de churn en gimnasio.
Produce 17 CSVs listos para importar en Odoo.

Uso:
    pip install pandas numpy faker
    python generar_datos_churn_gym.py

Configuración rápida: edita las constantes de la sección CONFIG.
"""

import os
import random
import warnings
from datetime import date, timedelta

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

N_CUSTOMERS = 500
N_CENTERS   = 5
N_TRAINERS  = 30
OUTPUT_DIR  = "odoo_synthetic_data"

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

try:
    from faker import Faker
    fake = Faker("es_ES")
    Faker.seed(SEED)
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False
    print("⚠  Faker no instalado. Se usarán nombres genéricos (pip install faker para nombres reales).")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

TODAY = date.today()

def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))

def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def save(df: pd.DataFrame, name: str):
    path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  ✓  {name}.csv  ({len(df):,} filas, {os.path.getsize(path)/1024:.0f} KB)")

def fake_name(gender=None):
    if HAS_FAKER:
        return fake.first_name_male() if gender == "H" else fake.first_name_female() if gender == "M" else fake.first_name()
    return f"Nombre{random.randint(1,9999)}"

def fake_surname():
    if HAS_FAKER:
        return f"{fake.last_name()} {fake.last_name()}"
    return f"Apellido{random.randint(1,9999)}"

def fake_person_name():
    if HAS_FAKER:
        return fake.name()
    return f"Persona {random.randint(1,999)}"

# ══════════════════════════════════════════════════════════════════════════════
# LATENT CHURN RISK  (variable oculta que correlaciona todos los módulos)
# ══════════════════════════════════════════════════════════════════════════════
# Beta(2,4) → distribución asimétrica a la izquierda: mayoría de clientes fieles

churn_risk = np.random.beta(2, 4, N_CUSTOMERS)   # 0=fiel, 1=abandona seguro

# ══════════════════════════════════════════════════════════════════════════════
# 1. CENTROS DEPORTIVOS
# ══════════════════════════════════════════════════════════════════════════════

CIUDADES = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao"]
CENTRO_NOMBRES = [
    "FitLife Madrid Centro",
    "FitLife Barcelona Gràcia",
    "FitLife Valencia Norte",
    "FitLife Sevilla Este",
    "FitLife Bilbao",
]
CP_POR_CIUDAD = {
    "Madrid":    ["28001","28002","28010","28020","28030"],
    "Barcelona": ["08001","08010","08015","08025","08030"],
    "Valencia":  ["46001","46010","46015","46020","46025"],
    "Sevilla":   ["41001","41010","41013","41018","41020"],
    "Bilbao":    ["48001","48002","48005","48010","48012"],
}

rows = []
for cid in range(1, N_CENTERS + 1):
    apertura = rand_date(date(2010, 1, 1), date(2018, 12, 31))
    rows.append({
        "id":                          cid,
        "nombre":                      CENTRO_NOMBRES[cid - 1],
        "ciudad":                      CIUDADES[cid - 1],
        "director":                    fake_person_name(),
        "fecha_apertura":              apertura,
        # instalaciones
        "piscina":                     random.random() > 0.4,
        "spa":                         random.random() > 0.5,
        "parking":                     random.random() > 0.3,
        "sala_crossfit":               True,
        "sala_yoga":                   True,
        "sala_funcional":              True,
        # operación
        "ocupacion_media_pct":         round(random.uniform(50, 85), 1),
        "ocupacion_hora_punta_pct":    round(random.uniform(75, 98), 1),
        "aforo_maximo":                random.choice([300, 350, 400, 450, 500]),
        "horario":                     "06:00–23:00",
        # personal
        "num_entrenadores":            random.randint(8, 20),
        "cambio_reciente_director":    random.random() < 0.2,
        "rotacion_entrenadores_pct":   round(random.uniform(5, 30), 1),
        # calidad
        "nps_centro":                  random.randint(20, 75),
        "valoracion_media":            round(random.uniform(3.5, 4.8), 1),
        "limpieza_valoracion":         round(random.uniform(3.2, 5.0), 1),
        "incidencias_abiertas":        random.randint(0, 15),
        # competencia
        "competidor_cercano":          random.choice(["Anytime Fitness","Holmes Place","VivaGym","McFIT","Altafit"]),
        "distancia_competidor_km":     round(random.uniform(0.3, 5.0), 1),
        "fecha_apertura_competidor":   rand_date(apertura, TODAY),
        # marketing
        "promocion_activa":            random.random() > 0.5,
        "evento_activo":               random.random() > 0.6,
        "campana_local":               random.random() > 0.7,
    })

df_centros = pd.DataFrame(rows)
save(df_centros, "centros_deportivos")

# ══════════════════════════════════════════════════════════════════════════════
# 2. EMPLEADOS / ENTRENADORES
# ══════════════════════════════════════════════════════════════════════════════

ESPECIALIDADES = ["Musculación","Cardio","CrossFit","Yoga","Pilates",
                  "Natación","Funcional","Nutrición","Boxing"]

rows = []
for eid in range(1, N_TRAINERS + 1):
    alta = rand_date(date(2015, 1, 1), date(2024, 1, 1))
    rows.append({
        "id":                      eid,
        "nombre":                  fake_name(),
        "apellidos":               fake_surname(),
        "centro_id":               random.randint(1, N_CENTERS),
        "fecha_alta":              alta,
        "antiguedad_anos":         round((TODAY - alta).days / 365, 1),
        "especialidad":            random.choice(ESPECIALIDADES),
        "ratio_clientes":          random.randint(10, 40),
        "horas_disponibles_semana":random.choice([20, 25, 30, 35, 40]),
        "valoracion":              round(random.uniform(2.5, 5.0), 1),
        "cambio_reciente":         random.random() < 0.15,
    })

df_empleados = pd.DataFrame(rows)
save(df_empleados, "empleados_entrenadores")

# ══════════════════════════════════════════════════════════════════════════════
# 3. CONTACTOS (clientes)
# ══════════════════════════════════════════════════════════════════════════════

OBJETIVOS = ["Perder peso","Ganar masa muscular","Mantenimiento","Rendimiento deportivo",
             "Rehabilitación","Bienestar general","Competición"]
SEGMENTOS  = ["Básico","Estándar","Premium","VIP"]

rows = []
for i in range(N_CUSTOMERS):
    r = churn_risk[i]
    centro_id = random.randint(1, N_CENTERS)
    ciudad    = CIUDADES[centro_id - 1]

    edad = int(clamp(random.gauss(35, 12), 16, 75))
    sexo = random.choice(["Hombre", "Mujer"])
    dob  = TODAY - timedelta(days=edad * 365 + random.randint(0, 364))

    # clientes más nuevos tienen más riesgo
    antiguedad_dias = int(clamp(np.random.exponential(500) * (1 - r * 0.4), 30, 365 * 5))
    fecha_alta = TODAY - timedelta(days=antiguedad_dias)

    estado    = "Baja" if random.random() < r * 0.6 else "Activo"
    distancia = round(clamp(random.gauss(3 + r * 5, 2), 0.1, 25), 1)

    seg_probs = [0.45, 0.30, 0.18, 0.07] if r > 0.5 else [0.20, 0.35, 0.30, 0.15]

    rows.append({
        "id":                  i + 1,
        "nombre":              fake_name(sexo[0]),
        "apellidos":           fake_surname(),
        "edad":                edad,
        "sexo":                sexo,
        "fecha_nacimiento":    dob,
        "codigo_postal":       random.choice(CP_POR_CIUDAD[ciudad]),
        "ciudad":              ciudad,
        "distancia_gimnasio_km": distancia,
        "fecha_alta":          fecha_alta,
        "estado":              estado,
        "segmento":            np.random.choice(SEGMENTOS, p=seg_probs),
        "objetivo_deportivo":  random.choice(OBJETIVOS),
        "centro_id":           centro_id,
        "entrenador_asignado_id": random.randint(1, N_TRAINERS),
    })

df_contactos = pd.DataFrame(rows)
# guardamos riesgo latente aparte para uso interno
df_contactos["_risk"] = churn_risk
save(df_contactos.drop(columns=["_risk"]), "contactos")

# ══════════════════════════════════════════════════════════════════════════════
# 4. CRM
# ══════════════════════════════════════════════════════════════════════════════

CANALES  = ["Web","Referido","Redes Sociales","Publicidad exterior","Email Marketing",
            "Google Ads","Visita directa","Evento","Influencer"]
CAMPANAS = ["Enero Nuevo Año","Verano Active","Black Friday","Vuelta al Cole",
            "San Valentín Fit","Campaña Local","Orgánico"]
OFERTAS  = ["1 mes gratis","2x1 primer trimestre","Descuento 20%","Sin matrícula",
            "Pack Familiar","Precio especial online","Ninguna"]

rows = []
for i, row in df_contactos.iterrows():
    r        = churn_risk[i]
    f_alta   = pd.to_datetime(row["fecha_alta"]).date()
    dias_prev = random.randint(1, 60)
    f_visita  = f_alta - timedelta(days=dias_prev)
    lead_score = int(clamp(random.gauss(70 - r * 30, 15), 10, 100))
    rows.append({
        "cliente_id":           row["id"],
        "canal_captacion":      random.choice(CANALES),
        "comercial_asignado":   f"Comercial_{random.randint(1, 8)}",
        "lead_score":           lead_score,
        "fecha_primera_visita": f_visita,
        "fecha_conversion":     f_alta,
        "num_llamadas":         random.randint(0, 8),
        "num_reuniones":        random.randint(0, 3),
        "oferta_aceptada":      random.choice(OFERTAS),
        "campana_origen":       random.choice(CAMPANAS),
        "tiempo_hasta_cierre_dias": int(clamp(dias_prev * random.uniform(0.5, 1.0), 1, 60)),
    })

df_crm = pd.DataFrame(rows)
save(df_crm, "crm_leads")

# ══════════════════════════════════════════════════════════════════════════════
# 5. VENTAS / SERVICIOS
# ══════════════════════════════════════════════════════════════════════════════

PLANES = {
    "Básico":       29.99,
    "Estándar":     44.99,
    "Premium":      64.99,
    "VIP":          99.99,
    "Solo Clases":  34.99,
    "Acceso Total": 79.99,
}
PLAN_NAMES  = list(PLANES.keys())
PLAN_PROBS_BAJO_RIESGO  = [0.10, 0.20, 0.30, 0.20, 0.10, 0.10]
PLAN_PROBS_ALTO_RIESGO  = [0.40, 0.30, 0.15, 0.05, 0.08, 0.02]

rows = []
for i, row in df_contactos.iterrows():
    r = churn_risk[i]
    probs = [a * (1 - r) + b * r for a, b in zip(PLAN_PROBS_BAJO_RIESGO, PLAN_PROBS_ALTO_RIESGO)]
    probs = np.array(probs); probs /= probs.sum()
    plan  = np.random.choice(PLAN_NAMES, p=probs)
    precio = PLANES[plan]
    n_compras = int(clamp(random.gauss(3 - r * 2, 2), 0, 15))
    rows.append({
        "cliente_id":              row["id"],
        "plan_contratado":         plan,
        "precio_plan":             precio,
        "entrenador_personal":     random.random() > (0.5 + r * 0.3),
        "nutricionista":           random.random() > (0.7 + r * 0.2),
        "spa":                     random.random() > 0.65,
        "piscina":                 random.random() > 0.55,
        "clases_premium":          random.random() > (0.4 + r * 0.3),
        "servicios_adicionales":   random.choice(
            ["Ninguno","Taquilla","Toalla","Taquilla + Toalla","Parking","Parking + Taquilla"]
        ),
        "num_compras_adicionales": n_compras,
        "importe_total_compras":   round(n_compras * random.uniform(10, 80), 2),
    })

df_ventas = pd.DataFrame(rows)
save(df_ventas, "ventas_servicios")

# ══════════════════════════════════════════════════════════════════════════════
# 6. SUSCRIPCIONES
# ══════════════════════════════════════════════════════════════════════════════

rows = []
for i, row in df_contactos.iterrows():
    r        = churn_risk[i]
    f_alta   = pd.to_datetime(row["fecha_alta"]).date()
    precio   = df_ventas.loc[i, "precio_plan"]
    ant_m    = int((TODAY - f_alta).days / 30)
    n_renov  = max(0, ant_m - 1)
    n_cancel = int(clamp(np.random.poisson(r * 2), 0, 5))
    prox_ren = TODAY + timedelta(days=random.randint(1, 30))
    ult_sub  = rand_date(f_alta, TODAY) if ant_m > 3 else None
    rows.append({
        "cliente_id":                   row["id"],
        "fecha_inicio":                 f_alta,
        "fecha_proxima_renovacion":     prox_ren,
        "renovacion_automatica":        random.random() > (r * 0.55),
        "antiguedad_meses":             ant_m,
        "num_renovaciones":             n_renov,
        "num_cancelaciones_anteriores": n_cancel,
        "precio_mensual":               round(precio * random.uniform(0.85, 1.15), 2),
        "ultima_subida_precio":         ult_sub,
        "dias_hasta_renovacion":        (prox_ren - TODAY).days,
    })

df_suscripciones = pd.DataFrame(rows)
save(df_suscripciones, "suscripciones")

# ══════════════════════════════════════════════════════════════════════════════
# 7. FACTURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

METODOS_PAGO = ["Domiciliación bancaria","Tarjeta crédito","Tarjeta débito",
                "PayPal","Efectivo","Bizum"]
MP_PROBS     = [0.50, 0.25, 0.10, 0.08, 0.05, 0.02]

rows = []
for i, row in df_contactos.iterrows():
    r         = churn_risk[i]
    ant_m     = df_suscripciones.loc[i, "antiguedad_meses"]
    precio_m  = df_suscripciones.loc[i, "precio_mensual"]
    total     = round(precio_m * ant_m * random.uniform(0.9, 1.1), 2)
    ult_pago  = TODAY - timedelta(days=int(clamp(random.gauss(15 + r * 20, 10), 1, 90)))
    desc      = random.choice([0, 0, 0, 5, 10, 15, 20, 25])
    rows.append({
        "cliente_id":              row["id"],
        "metodo_pago":             np.random.choice(METODOS_PAGO, p=MP_PROBS),
        "num_pagos_rechazados":    int(clamp(np.random.poisson(r * 2), 0, 10)),
        "retrasos_en_pagos":       int(clamp(np.random.poisson(r * 1.5), 0, 8)),
        "cuotas_pendientes":       int(clamp(np.random.poisson(r * 1), 0, 4)),
        "descuento_activo_pct":    desc,
        "ultimo_pago":             ult_pago,
        "importe_total_facturado": total,
        "lifetime_value_clv":      round(total * random.uniform(1.0, 2.5), 2),
    })

df_facturacion = pd.DataFrame(rows)
save(df_facturacion, "facturacion")

# ══════════════════════════════════════════════════════════════════════════════
# 8. MARKETING AUTOMATION
# ══════════════════════════════════════════════════════════════════════════════

rows = []
for i, row in df_contactos.iterrows():
    r = churn_risk[i]
    emails_env   = random.randint(5, 50)
    tasa_apertura = clamp(random.gauss(0.35 - r * 0.20, 0.10), 0.02, 0.90)
    emails_ab    = int(emails_env * tasa_apertura)
    ctr          = round(clamp(random.gauss(0.05 - r * 0.03, 0.02), 0.0, 0.30), 3)
    sms_env      = random.randint(0, 20)
    sms_ab       = int(sms_env * clamp(random.gauss(0.6 - r * 0.3, 0.1), 0.05, 1.0))
    push_ab      = max(0, int(random.gauss(10 - r * 8, 3)))
    ult_int_dias = int(clamp(random.gauss(7 + r * 60, 15), 1, 180))
    campanas_rec = random.randint(1, 12)
    campanas_conv = int(campanas_rec * clamp(random.gauss(0.2 - r * 0.15, 0.08), 0, 0.8))
    rows.append({
        "cliente_id":                   row["id"],
        "emails_enviados":              emails_env,
        "emails_abiertos":              emails_ab,
        "ctr_emails":                   ctr,
        "sms_enviados":                 sms_env,
        "sms_abiertos":                 sms_ab,
        "push_notifications_abiertas":  push_ab,
        "ultima_interaccion_hace_dias": ult_int_dias,
        "campanas_recibidas":           campanas_rec,
        "campanas_convertidas":         campanas_conv,
    })

df_marketing = pd.DataFrame(rows)
save(df_marketing, "marketing_automation")

# ══════════════════════════════════════════════════════════════════════════════
# 9. ENCUESTAS
# ══════════════════════════════════════════════════════════════════════════════

COMENTARIOS_POS = [
    "Muy satisfecho con las instalaciones.",
    "El equipo de entrenadores es excelente.",
    "Las clases son variadas y motivadoras.",
    "Recomendaría este gimnasio sin dudarlo.",
    "La atención al cliente es de 10.",
    "Me encanta el ambiente y la limpieza.",
]
COMENTARIOS_NEG = [
    "Las máquinas a veces están estropeadas.",
    "Demasiada gente en hora punta.",
    "El precio ha subido mucho últimamente.",
    "Cambio de entrenador sin previo aviso.",
    "La limpieza podría mejorar.",
    "Las duchas necesitan renovación.",
    "Difícil aparcar.",
    "Me han cobrado de más un mes.",
]

rows = []
for i, row in df_contactos.iterrows():
    r = churn_risk[i]
    # clientes con alto riesgo responden menos
    if random.random() < 0.15 + r * 0.35:
        continue
    nps = int(clamp(random.gauss(7 - r * 5, 2), 0, 10))
    val_ent = round(clamp(random.gauss(4.0 - r * 1.5, 0.8), 1.0, 5.0), 1)
    val_ins = round(clamp(random.gauss(4.0 - r * 1.5, 0.8), 1.0, 5.0), 1)
    val_lim = round(clamp(random.gauss(3.8 - r * 1.5, 0.8), 1.0, 5.0), 1)
    val_cla = round(clamp(random.gauss(4.1 - r * 1.5, 0.8), 1.0, 5.0), 1)
    if nps >= 7:
        comentario = random.choice(COMENTARIOS_POS) if random.random() < 0.5 else ""
    else:
        comentario = random.choice(COMENTARIOS_NEG) if random.random() < 0.7 else ""
    rows.append({
        "cliente_id":             row["id"],
        "nps":                    nps,
        "valoracion_entrenador":  val_ent,
        "valoracion_instalaciones": val_ins,
        "valoracion_limpieza":    val_lim,
        "valoracion_clases":      val_cla,
        "comentarios":            comentario,
    })

df_encuestas = pd.DataFrame(rows)
save(df_encuestas, "encuestas_satisfaccion")

# ══════════════════════════════════════════════════════════════════════════════
# 10. EVENTOS
# ══════════════════════════════════════════════════════════════════════════════

rows = []
for i, row in df_contactos.iterrows():
    r = churn_risk[i]
    rows.append({
        "cliente_id":                  row["id"],
        "eventos_asistidos":           max(0, int(random.gauss(3 - r * 2.5, 2))),
        "participacion_retos":         random.random() > (0.3 + r * 0.5),
        "participacion_masterclass":   random.random() > (0.4 + r * 0.4),
        "participacion_competiciones": random.random() > (0.7 + r * 0.25),
        "participacion_promociones":   random.random() > (0.4 + r * 0.4),
    })

df_eventos = pd.DataFrame(rows)
save(df_eventos, "eventos_participacion")

# ══════════════════════════════════════════════════════════════════════════════
# 11. HELPDESK
# ══════════════════════════════════════════════════════════════════════════════

TIPOS_INCIDENCIA = [
    "Problema con tarjeta de acceso","Error en factura","Queja instalaciones",
    "Solicitud de congelación","Cambio de plan","Incidencia con entrenador",
    "Problema con reserva de clase","Solicitud de baja","Otros",
]

rows = []
for i, row in df_contactos.iterrows():
    r = churn_risk[i]
    n_tickets = int(clamp(np.random.poisson(0.5 + r * 3), 0, 12))
    if n_tickets == 0:
        rows.append({
            "cliente_id":                      row["id"],
            "num_tickets":                     0,
            "tipo_incidencia_principal":       None,
            "incidencias_abiertas":            0,
            "tiempo_medio_resolucion_dias":    None,
            "ultima_incidencia":               None,
            "reclamaciones":                   0,
        })
    else:
        rows.append({
            "cliente_id":                      row["id"],
            "num_tickets":                     n_tickets,
            "tipo_incidencia_principal":       random.choice(TIPOS_INCIDENCIA),
            "incidencias_abiertas":            int(clamp(np.random.poisson(r), 0, n_tickets)),
            "tiempo_medio_resolucion_dias":    round(clamp(random.gauss(2 + r * 3, 1), 0.5, 20), 1),
            "ultima_incidencia":               TODAY - timedelta(days=random.randint(1, 365)),
            "reclamaciones":                   int(clamp(np.random.poisson(r * 1.5), 0, 5)),
        })

df_helpdesk = pd.DataFrame(rows)
save(df_helpdesk, "helpdesk_tickets")

# ══════════════════════════════════════════════════════════════════════════════
# 12. MANTENIMIENTO  (por centro)
# ══════════════════════════════════════════════════════════════════════════════

rows = []
for cid in range(1, N_CENTERS + 1):
    ult_averia     = TODAY - timedelta(days=random.randint(0, 90))
    fecha_rep      = ult_averia + timedelta(days=random.randint(1, 14))
    rows.append({
        "centro_id":                cid,
        "maquinas_fuera_de_servicio": random.randint(0, 10),
        "fecha_ultima_averia":      ult_averia,
        "fecha_reparacion":         fecha_rep if fecha_rep <= TODAY else None,
        "fecha_renovacion_cardio":  rand_date(date(2020, 1, 1), date(2025, 6, 1)),
        "fecha_renovacion_fuerza":  rand_date(date(2019, 1, 1), date(2024, 12, 1)),
        "horas_acumuladas_uso":     random.randint(5_000, 50_000),
    })

df_mantenimiento = pd.DataFrame(rows)
save(df_mantenimiento, "mantenimiento")

# ══════════════════════════════════════════════════════════════════════════════
# 13. INVENTARIO  (por centro)
# ══════════════════════════════════════════════════════════════════════════════

rows = []
for cid in range(1, N_CENTERS + 1):
    rows.append({
        "centro_id":                        cid,
        "num_cintas":                       random.randint(10, 40),
        "num_bicicletas":                   random.randint(15, 50),
        "num_maquinas_fuerza":              random.randint(20, 80),
        "material_funcional_disponible":    random.choice(["Completo","Parcial","Limitado"]),
        "nuevas_adquisiciones_ultimo_anio": random.randint(0, 20),
        "equipamiento_retirado_ultimo_anio":random.randint(0, 15),
    })

df_inventario = pd.DataFrame(rows)
save(df_inventario, "inventario")

# ══════════════════════════════════════════════════════════════════════════════
# 14. REGISTRO DE ACCESOS
# ══════════════════════════════════════════════════════════════════════════════

CLASES_POSIBLES = [
    "Spinning","Yoga","Pilates","CrossFit","Zumba","Body Pump",
    "Natación","Funcional","Boxing","Stretching",
    None, None, None,   # sin clase = entrenamiento libre
]
HORAS = ["07:00","07:30","08:00","09:00","10:00","11:00",
         "12:00","17:00","18:00","19:00","20:00","21:00"]
TIPOS_ACCESO = ["Torniquete","App","QR","Tarjeta"]

rows = []
for i, row in df_contactos.iterrows():
    r          = churn_risk[i]
    f_alta     = pd.to_datetime(row["fecha_alta"]).date()
    ant_dias   = (TODAY - f_alta).days
    frec_sem   = clamp(random.gauss(3 - r * 2.5, 0.8), 0.2, 6)
    n_accesos  = min(int(frec_sem * ant_dias / 7), 500)
    for _ in range(n_accesos):
        dias_atras   = random.randint(0, ant_dias)
        fecha_acceso = TODAY - timedelta(days=dias_atras)
        rows.append({
            "cliente_id":               row["id"],
            "centro_id":                row["centro_id"],
            "fecha":                    fecha_acceso,
            "hora":                     random.choice(HORAS),
            "tipo_acceso":              random.choice(TIPOS_ACCESO),
            "clase_asistida":           random.choice(CLASES_POSIBLES),
            "duracion_entrenamiento_min": random.randint(30, 120),
        })

df_accesos = pd.DataFrame(rows)
save(df_accesos, "registro_accesos")

# ══════════════════════════════════════════════════════════════════════════════
# 15. ACTIVIDAD DEPORTIVA  (agregada por cliente)
# ══════════════════════════════════════════════════════════════════════════════

TENDENCIAS = ["Creciente","Estable","Decreciente"]

rows = []
for i, row in df_contactos.iterrows():
    r      = churn_risk[i]
    frec   = clamp(random.gauss(3 - r * 2.5, 1), 0, 7)
    v7     = max(0, int(random.gauss(frec, 1)))
    v30    = max(v7, int(random.gauss(frec * 4, 3)))
    v90    = max(v30, int(random.gauss(frec * 12, 6)))
    dias_u = int(clamp(random.gauss(5 + r * 40, 10), 0, 180))

    probs_tend = np.array([
        clamp(0.40 - r * 0.40, 0.02, 0.95),
        clamp(0.35 - r * 0.10, 0.02, 0.95),
        clamp(0.25 + r * 0.50, 0.02, 0.95),
    ])
    probs_tend /= probs_tend.sum()
    tendencia  = np.random.choice(TENDENCIAS, p=probs_tend)

    cl_res  = max(0, int(random.gauss(v30 * 0.8, 3)))
    cl_can  = max(0, int(random.gauss(cl_res * r * 0.5, 2)))
    cl_asis = max(0, cl_res - cl_can)

    rows.append({
        "cliente_id":                       row["id"],
        "visitas_ultimos_7_dias":           v7,
        "visitas_ultimos_30_dias":          v30,
        "visitas_ultimos_90_dias":          v90,
        "dias_desde_ultima_visita":         dias_u,
        "tendencia_asistencia":             tendencia,
        "clases_reservadas_mes":            cl_res,
        "clases_canceladas_mes":            cl_can,
        "clases_asistidas_mes":             cl_asis,
        "entrenamientos_personales_mes":    max(0, int(random.gauss(1 - r * 0.8, 1))),
        "uso_piscina_mes":                  max(0, int(random.gauss(2 - r * 1.5, 2))),
        "uso_spa_mes":                      max(0, int(random.gauss(1 - r * 0.8, 1))),
    })

df_actividad = pd.DataFrame(rows)
save(df_actividad, "actividad_deportiva")

# ══════════════════════════════════════════════════════════════════════════════
# 16. ENGAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

rows = []
for i, row in df_contactos.iterrows():
    r = churn_risk[i]
    rows.append({
        "cliente_id":                    row["id"],
        "dias_desde_ultimo_acceso_app":  int(clamp(random.gauss(5 + r * 60, 15), 0, 180)),
        "entrenamientos_registrados":    max(0, int(random.gauss(20 - r * 18, 8))),
        "peso_registrado":               random.random() > (0.3 + r * 0.5),
        "objetivos_actualizados":        random.random() > (0.4 + r * 0.4),
        "racha_entrenamiento_dias":      max(0, int(random.gauss(10 - r * 9, 5))),
        "invitaciones_realizadas":       max(0, int(random.gauss(1 - r * 0.8, 1))),
        "participacion_retos":           random.random() > (0.4 + r * 0.5),
        "engagement_score":              int(clamp(100 * (1 - r) * random.uniform(0.8, 1.2), 5, 100)),
    })

df_engagement = pd.DataFrame(rows)
save(df_engagement, "engagement")

# ══════════════════════════════════════════════════════════════════════════════
# 17. CUSTOMER HEALTH  (output del modelo de IA)
# ══════════════════════════════════════════════════════════════════════════════

MOTIVOS = [
    "Baja frecuencia de visitas",
    "Impagos recurrentes",
    "Baja satisfacción (NPS < 5)",
    "Sin interacción con la app",
    "Alta distancia al gimnasio",
    "Precio elevado respecto al uso",
    "Cancelaciones de clases frecuentes",
    "Cambio reciente de entrenador",
    "Sin renovación automática",
    "Competidor cercano recién abierto",
]

ACCIONES = {
    "alto":  ["Llamada urgente del comercial",
              "Ofrecer congelación temporal de cuota",
              "Aplicar descuento personalizado del 20%",
              "Reunión con el director del centro"],
    "medio": ["Enviar email personalizado de reactivación",
              "Ofrecer sesión de entrenamiento personal gratuita",
              "Invitar a evento exclusivo del centro",
              "Aplicar descuento del 10%"],
    "bajo":  ["Email de fidelización estándar",
              "Push notification con novedades del centro",
              "Enviar encuesta de satisfacción"],
}

rows = []
for i, row in df_contactos.iterrows():
    r = churn_risk[i]
    health   = int(clamp(100 * (1 - r) * random.uniform(0.85, 1.15), 5, 100))
    churn_p  = round(clamp(r * 100 * random.uniform(0.9, 1.1), 0.1, 99.9), 1)
    precio_m = df_suscripciones.loc[i, "precio_mensual"]
    meses_est = max(1, int(random.gauss(24 * (1 - r), 12)))
    clv_est  = round(precio_m * meses_est, 2)

    n_vars   = random.randint(2, 4)
    vars_inf = "; ".join(random.sample(MOTIVOS, n_vars))
    motivo   = random.choice(MOTIVOS)

    nivel = "alto" if churn_p >= 60 else "medio" if churn_p >= 30 else "bajo"
    accion = random.choice(ACCIONES[nivel])

    if nivel == "alto":
        expl = (f"El cliente presenta señales críticas: {motivo.lower()}. "
                f"Tendencia de actividad decreciente. Intervención inmediata recomendada.")
    elif nivel == "medio":
        expl = (f"El cliente muestra indicios de desenganche: {motivo.lower()}. "
                f"Una acción proactiva puede revertir la situación.")
    else:
        expl = (f"El cliente está en buen estado. Mantener acciones de fidelización. "
                f"Vigilar: {motivo.lower()}.")

    rows.append({
        "cliente_id":                       row["id"],
        "health_score":                     health,
        "riesgo_churn_pct":                 churn_p,
        "customer_lifetime_value_estimado": clv_est,
        "fecha_ultima_prediccion":          TODAY,
        "variables_mas_influyentes":        vars_inf,
        "motivo_principal_riesgo":          motivo,
        "explicacion_ia":                   expl,
        "accion_recomendada":               accion,
        "nivel_riesgo":                     nivel,
    })

df_health = pd.DataFrame(rows)
save(df_health, "customer_health")

# ══════════════════════════════════════════════════════════════════════════════
# 18. COHORTE ESPECIAL: riesgo de baja pre-verano
# ══════════════════════════════════════════════════════════════════════════════
# Perfil objetivo: adulto que se apuntó hace 6-12 meses y lleva los últimos
# ~3 meses sin ir al gimnasio (o yendo con frecuencia muy baja). Al ejecutarse
# el análisis cerca del verano (TODAY), esta inactividad reciente coincide con
# la temporada. La relación con el churn es estadística, no determinista:
# la mayoría termina de baja, pero una parte sigue "Activo" — son los casos
# que la demo debe detectar a tiempo para lanzar la acción comercial
# (SMS ofreciendo pausar la suscripción 1 mes).

N_COHORT           = 70
COHORT_CHURN_RATE  = 0.70   # proporción del grupo que ya está de Baja

cohort_risk = np.random.uniform(0.65, 0.95, N_COHORT)
cohort_ids  = list(range(N_CUSTOMERS + 1, N_CUSTOMERS + 1 + N_COHORT))

# --- contactos ---
rows = []
for j, cid in enumerate(cohort_ids):
    r = cohort_risk[j]
    centro_id = random.randint(1, N_CENTERS)
    ciudad    = CIUDADES[centro_id - 1]
    edad = random.randint(28, 55)                      # adulto
    sexo = random.choice(["Hombre", "Mujer"])
    dob  = TODAY - timedelta(days=edad * 365 + random.randint(0, 364))
    antiguedad_dias = random.randint(180, 365)          # alta hace 6-12 meses
    fecha_alta = TODAY - timedelta(days=antiguedad_dias)
    estado    = "Baja" if random.random() < COHORT_CHURN_RATE else "Activo"
    distancia = round(clamp(random.gauss(3 + r * 5, 2), 0.1, 25), 1)
    rows.append({
        "id":                  cid,
        "nombre":              fake_name(sexo[0]),
        "apellidos":           fake_surname(),
        "edad":                edad,
        "sexo":                sexo,
        "fecha_nacimiento":    dob,
        "codigo_postal":       random.choice(CP_POR_CIUDAD[ciudad]),
        "ciudad":              ciudad,
        "distancia_gimnasio_km": distancia,
        "fecha_alta":          fecha_alta,
        "estado":              estado,
        "segmento":            np.random.choice(SEGMENTOS, p=[0.30, 0.35, 0.25, 0.10]),
        "objetivo_deportivo":  random.choice(OBJETIVOS),
        "centro_id":           centro_id,
        "entrenador_asignado_id": random.randint(1, N_TRAINERS),
    })
df_contactos_cohort = pd.DataFrame(rows)

# --- crm_leads ---
rows = []
for j, cid in enumerate(cohort_ids):
    r        = cohort_risk[j]
    row      = df_contactos_cohort.iloc[j]
    f_alta   = row["fecha_alta"]
    dias_prev = random.randint(1, 60)
    f_visita  = f_alta - timedelta(days=dias_prev)
    lead_score = int(clamp(random.gauss(70 - r * 30, 15), 10, 100))
    rows.append({
        "cliente_id":           cid,
        "canal_captacion":      random.choice(CANALES),
        "comercial_asignado":   f"Comercial_{random.randint(1, 8)}",
        "lead_score":           lead_score,
        "fecha_primera_visita": f_visita,
        "fecha_conversion":     f_alta,
        "num_llamadas":         random.randint(0, 8),
        "num_reuniones":        random.randint(0, 3),
        "oferta_aceptada":      random.choice(OFERTAS),
        "campana_origen":       random.choice(CAMPANAS),
        "tiempo_hasta_cierre_dias": int(clamp(dias_prev * random.uniform(0.5, 1.0), 1, 60)),
    })
df_crm_cohort = pd.DataFrame(rows)

# --- ventas_servicios ---
rows = []
for j, cid in enumerate(cohort_ids):
    r = cohort_risk[j]
    probs = [a * (1 - r) + b * r for a, b in zip(PLAN_PROBS_BAJO_RIESGO, PLAN_PROBS_ALTO_RIESGO)]
    probs = np.array(probs); probs /= probs.sum()
    plan  = np.random.choice(PLAN_NAMES, p=probs)
    precio = PLANES[plan]
    n_compras = int(clamp(random.gauss(3 - r * 2, 2), 0, 15))
    rows.append({
        "cliente_id":              cid,
        "plan_contratado":         plan,
        "precio_plan":             precio,
        "entrenador_personal":     random.random() > (0.5 + r * 0.3),
        "nutricionista":           random.random() > (0.7 + r * 0.2),
        "spa":                     random.random() > 0.65,
        "piscina":                 random.random() > 0.55,
        "clases_premium":          random.random() > (0.4 + r * 0.3),
        "servicios_adicionales":   random.choice(
            ["Ninguno","Taquilla","Toalla","Taquilla + Toalla","Parking","Parking + Taquilla"]
        ),
        "num_compras_adicionales": n_compras,
        "importe_total_compras":   round(n_compras * random.uniform(10, 80), 2),
    })
df_ventas_cohort = pd.DataFrame(rows)

# --- suscripciones ---
rows = []
for j, cid in enumerate(cohort_ids):
    r        = cohort_risk[j]
    f_alta   = df_contactos_cohort.iloc[j]["fecha_alta"]
    precio   = df_ventas_cohort.iloc[j]["precio_plan"]
    ant_m    = int((TODAY - f_alta).days / 30)
    n_renov  = max(0, ant_m - 1)
    n_cancel = int(clamp(np.random.poisson(r * 2), 0, 5))
    prox_ren = TODAY + timedelta(days=random.randint(1, 30))
    ult_sub  = rand_date(f_alta, TODAY) if ant_m > 3 else None
    rows.append({
        "cliente_id":                   cid,
        "fecha_inicio":                 f_alta,
        "fecha_proxima_renovacion":     prox_ren,
        "renovacion_automatica":        random.random() > (r * 0.55),
        "antiguedad_meses":             ant_m,
        "num_renovaciones":             n_renov,
        "num_cancelaciones_anteriores": n_cancel,
        "precio_mensual":               round(precio * random.uniform(0.85, 1.15), 2),
        "ultima_subida_precio":         ult_sub,
        "dias_hasta_renovacion":        (prox_ren - TODAY).days,
    })
df_suscripciones_cohort = pd.DataFrame(rows)

# --- facturacion ---
rows = []
for j, cid in enumerate(cohort_ids):
    r         = cohort_risk[j]
    ant_m     = df_suscripciones_cohort.iloc[j]["antiguedad_meses"]
    precio_m  = df_suscripciones_cohort.iloc[j]["precio_mensual"]
    total     = round(precio_m * ant_m * random.uniform(0.9, 1.1), 2)
    ult_pago  = TODAY - timedelta(days=int(clamp(random.gauss(15 + r * 20, 10), 1, 90)))
    desc      = random.choice([0, 0, 0, 5, 10, 15, 20, 25])
    rows.append({
        "cliente_id":              cid,
        "metodo_pago":             np.random.choice(METODOS_PAGO, p=MP_PROBS),
        "num_pagos_rechazados":    int(clamp(np.random.poisson(r * 2), 0, 10)),
        "retrasos_en_pagos":       int(clamp(np.random.poisson(r * 1.5), 0, 8)),
        "cuotas_pendientes":       int(clamp(np.random.poisson(r * 1), 0, 4)),
        "descuento_activo_pct":    desc,
        "ultimo_pago":             ult_pago,
        "importe_total_facturado": total,
        "lifetime_value_clv":      round(total * random.uniform(1.0, 2.5), 2),
    })
df_facturacion_cohort = pd.DataFrame(rows)

# --- marketing_automation ---
rows = []
for j, cid in enumerate(cohort_ids):
    r = cohort_risk[j]
    emails_env   = random.randint(5, 50)
    tasa_apertura = clamp(random.gauss(0.35 - r * 0.20, 0.10), 0.02, 0.90)
    emails_ab    = int(emails_env * tasa_apertura)
    ctr          = round(clamp(random.gauss(0.05 - r * 0.03, 0.02), 0.0, 0.30), 3)
    sms_env      = random.randint(0, 20)
    sms_ab       = int(sms_env * clamp(random.gauss(0.6 - r * 0.3, 0.1), 0.05, 1.0))
    push_ab      = max(0, int(random.gauss(10 - r * 8, 3)))
    ult_int_dias = int(clamp(random.gauss(7 + r * 60, 15), 1, 180))
    campanas_rec = random.randint(1, 12)
    campanas_conv = int(campanas_rec * clamp(random.gauss(0.2 - r * 0.15, 0.08), 0, 0.8))
    rows.append({
        "cliente_id":                   cid,
        "emails_enviados":              emails_env,
        "emails_abiertos":              emails_ab,
        "ctr_emails":                   ctr,
        "sms_enviados":                 sms_env,
        "sms_abiertos":                 sms_ab,
        "push_notifications_abiertas":  push_ab,
        "ultima_interaccion_hace_dias": ult_int_dias,
        "campanas_recibidas":           campanas_rec,
        "campanas_convertidas":         campanas_conv,
    })
df_marketing_cohort = pd.DataFrame(rows)

# --- encuestas_satisfaccion ---
rows = []
for j, cid in enumerate(cohort_ids):
    r = cohort_risk[j]
    if random.random() < 0.15 + r * 0.35:
        continue
    nps = int(clamp(random.gauss(7 - r * 5, 2), 0, 10))
    val_ent = round(clamp(random.gauss(4.0 - r * 1.5, 0.8), 1.0, 5.0), 1)
    val_ins = round(clamp(random.gauss(4.0 - r * 1.5, 0.8), 1.0, 5.0), 1)
    val_lim = round(clamp(random.gauss(3.8 - r * 1.5, 0.8), 1.0, 5.0), 1)
    val_cla = round(clamp(random.gauss(4.1 - r * 1.5, 0.8), 1.0, 5.0), 1)
    if nps >= 7:
        comentario = random.choice(COMENTARIOS_POS) if random.random() < 0.5 else ""
    else:
        comentario = random.choice(COMENTARIOS_NEG) if random.random() < 0.7 else ""
    rows.append({
        "cliente_id":             cid,
        "nps":                    nps,
        "valoracion_entrenador":  val_ent,
        "valoracion_instalaciones": val_ins,
        "valoracion_limpieza":    val_lim,
        "valoracion_clases":      val_cla,
        "comentarios":            comentario,
    })
df_encuestas_cohort = pd.DataFrame(rows)

# --- eventos_participacion ---
rows = []
for j, cid in enumerate(cohort_ids):
    r = cohort_risk[j]
    rows.append({
        "cliente_id":                  cid,
        "eventos_asistidos":           max(0, int(random.gauss(3 - r * 2.5, 2))),
        "participacion_retos":         random.random() > (0.3 + r * 0.5),
        "participacion_masterclass":   random.random() > (0.4 + r * 0.4),
        "participacion_competiciones": random.random() > (0.7 + r * 0.25),
        "participacion_promociones":   random.random() > (0.4 + r * 0.4),
    })
df_eventos_cohort = pd.DataFrame(rows)

# --- helpdesk_tickets ---
rows = []
for j, cid in enumerate(cohort_ids):
    r = cohort_risk[j]
    n_tickets = int(clamp(np.random.poisson(0.5 + r * 3), 0, 12))
    if n_tickets == 0:
        rows.append({
            "cliente_id": cid, "num_tickets": 0, "tipo_incidencia_principal": None,
            "incidencias_abiertas": 0, "tiempo_medio_resolucion_dias": None,
            "ultima_incidencia": None, "reclamaciones": 0,
        })
    else:
        rows.append({
            "cliente_id":                   cid,
            "num_tickets":                  n_tickets,
            "tipo_incidencia_principal":    random.choice(TIPOS_INCIDENCIA),
            "incidencias_abiertas":         int(clamp(np.random.poisson(r), 0, n_tickets)),
            "tiempo_medio_resolucion_dias": round(clamp(random.gauss(2 + r * 3, 1), 0.5, 20), 1),
            "ultima_incidencia":            TODAY - timedelta(days=random.randint(1, 365)),
            "reclamaciones":                int(clamp(np.random.poisson(r * 1.5), 0, 5)),
        })
df_helpdesk_cohort = pd.DataFrame(rows)

# --- actividad_deportiva ---
# Aquí se fuerza el patrón central de la cohorte: últimos ~3 meses sin ir
# (o yendo con frecuencia muy baja), con tendencia claramente decreciente.
rows = []
for j, cid in enumerate(cohort_ids):
    v7  = 0
    v30 = random.choice([0, 0, 0, 1])
    v90 = random.randint(0, 3)
    dias_u = random.randint(85, 150)
    tendencia = np.random.choice(TENDENCIAS, p=[0.03, 0.12, 0.85])
    cl_res  = max(0, int(random.gauss(1, 1)))
    cl_can  = max(0, int(random.gauss(cl_res * 0.6, 1)))
    cl_asis = max(0, cl_res - cl_can)
    rows.append({
        "cliente_id":                       cid,
        "visitas_ultimos_7_dias":           v7,
        "visitas_ultimos_30_dias":          v30,
        "visitas_ultimos_90_dias":          v90,
        "dias_desde_ultima_visita":         dias_u,
        "tendencia_asistencia":             tendencia,
        "clases_reservadas_mes":            cl_res,
        "clases_canceladas_mes":            cl_can,
        "clases_asistidas_mes":             cl_asis,
        "entrenamientos_personales_mes":    0,
        "uso_piscina_mes":                  max(0, int(random.gauss(0.3, 0.6))),
        "uso_spa_mes":                      max(0, int(random.gauss(0.2, 0.5))),
    })
df_actividad_cohort = pd.DataFrame(rows)

# --- engagement ---
# Motor principal de la señal: engagement_score bajo y app abandonada.
rows = []
for j, cid in enumerate(cohort_ids):
    rows.append({
        "cliente_id":                    cid,
        "dias_desde_ultimo_acceso_app":  random.randint(75, 150),
        "entrenamientos_registrados":    max(0, int(random.gauss(2, 2))),
        "peso_registrado":               random.random() > 0.85,
        "objetivos_actualizados":        random.random() > 0.85,
        "racha_entrenamiento_dias":      0,
        "invitaciones_realizadas":       max(0, int(random.gauss(0.2, 0.5))),
        "participacion_retos":           random.random() > 0.85,
        "engagement_score":              int(clamp(random.gauss(18, 10), 5, 40)),
    })
df_engagement_cohort = pd.DataFrame(rows)

# --- customer_health ---
rows = []
for j, cid in enumerate(cohort_ids):
    r = cohort_risk[j]
    health   = int(clamp(100 * (1 - r) * random.uniform(0.85, 1.15), 5, 100))
    churn_p  = round(clamp(r * 100 * random.uniform(0.9, 1.1), 0.1, 99.9), 1)
    precio_m = df_suscripciones_cohort.iloc[j]["precio_mensual"]
    meses_est = max(1, int(random.gauss(24 * (1 - r), 12)))
    clv_est  = round(precio_m * meses_est, 2)
    n_vars   = random.randint(2, 4)
    vars_inf = "; ".join(random.sample(MOTIVOS, n_vars))
    accion   = "Enviar SMS ofreciendo pausar la suscripción 1 mes"
    expl     = ("El cliente lleva ~3 meses sin acudir al centro tras 6-12 meses de alta, "
                "justo antes del verano. Riesgo de baja estacional. "
                "Acción recomendada: SMS ofreciendo pausar la suscripción 1 mes.")
    rows.append({
        "cliente_id":                       cid,
        "health_score":                     health,
        "riesgo_churn_pct":                 churn_p,
        "customer_lifetime_value_estimado": clv_est,
        "fecha_ultima_prediccion":          TODAY,
        "variables_mas_influyentes":        vars_inf,
        "motivo_principal_riesgo":          "Baja frecuencia de visitas",
        "explicacion_ia":                   expl,
        "accion_recomendada":               accion,
        "nivel_riesgo":                     "alto",
    })
df_health_cohort = pd.DataFrame(rows)

# --- fusionar cohorte con los datasets originales y re-guardar ---
df_contactos     = pd.concat([df_contactos, df_contactos_cohort], ignore_index=True)
df_crm           = pd.concat([df_crm, df_crm_cohort], ignore_index=True)
df_ventas        = pd.concat([df_ventas, df_ventas_cohort], ignore_index=True)
df_suscripciones = pd.concat([df_suscripciones, df_suscripciones_cohort], ignore_index=True)
df_facturacion   = pd.concat([df_facturacion, df_facturacion_cohort], ignore_index=True)
df_marketing     = pd.concat([df_marketing, df_marketing_cohort], ignore_index=True)
df_encuestas     = pd.concat([df_encuestas, df_encuestas_cohort], ignore_index=True)
df_eventos       = pd.concat([df_eventos, df_eventos_cohort], ignore_index=True)
df_helpdesk      = pd.concat([df_helpdesk, df_helpdesk_cohort], ignore_index=True)
df_actividad     = pd.concat([df_actividad, df_actividad_cohort], ignore_index=True)
df_engagement    = pd.concat([df_engagement, df_engagement_cohort], ignore_index=True)
df_health        = pd.concat([df_health, df_health_cohort], ignore_index=True)

save(df_contactos.drop(columns=["_risk"], errors="ignore"), "contactos")
save(df_crm, "crm_leads")
save(df_ventas, "ventas_servicios")
save(df_suscripciones, "suscripciones")
save(df_facturacion, "facturacion")
save(df_marketing, "marketing_automation")
save(df_encuestas, "encuestas_satisfaccion")
save(df_eventos, "eventos_participacion")
save(df_helpdesk, "helpdesk_tickets")
save(df_actividad, "actividad_deportiva")
save(df_engagement, "engagement")
save(df_health, "customer_health")

print(f"\n  Cohorte pre-verano añadida: {N_COHORT} clientes "
      f"({(df_contactos_cohort['estado']=='Baja').sum()} Baja / "
      f"{(df_contactos_cohort['estado']=='Activo').sum()} Activo)")

# risco combinado (original + cohorte) para el resumen final
churn_risk  = np.concatenate([churn_risk, cohort_risk])
N_CUSTOMERS = N_CUSTOMERS + N_COHORT

# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ══════════════════════════════════════════════════════════════════════════════

print()
print("═" * 58)
print(f"  Directorio de salida: ./{OUTPUT_DIR}/")
print("─" * 58)
archivos = sorted(os.listdir(OUTPUT_DIR))
total_kb = 0
for f in archivos:
    path = os.path.join(OUTPUT_DIR, f)
    kb = os.path.getsize(path) / 1024
    total_kb += kb
    print(f"  {f:<42}  {kb:>6.0f} KB")
print("─" * 58)
print(f"  {'TOTAL':<42}  {total_kb:>6.0f} KB")
print("═" * 58)

# Distribución de churn para referencia
bajo   = (churn_risk < 0.30).sum()
medio  = ((churn_risk >= 0.30) & (churn_risk < 0.60)).sum()
alto   = (churn_risk >= 0.60).sum()
print(f"\n  Distribución de riesgo latente en los {N_CUSTOMERS} clientes:")
print(f"    Bajo   (< 30 %)  →  {bajo:>3} clientes  ({bajo/N_CUSTOMERS*100:.0f} %)")
print(f"    Medio  (30–60 %) →  {medio:>3} clientes  ({medio/N_CUSTOMERS*100:.0f} %)")
print(f"    Alto   (> 60 %)  →  {alto:>3} clientes  ({alto/N_CUSTOMERS*100:.0f} %)")
print()
