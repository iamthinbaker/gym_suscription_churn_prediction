{
    "name": "Gym Backoffice",
    "summary": "Herramienta de gestión de un gimnasio con IA para predecir abandono de cliente",
    "version": "19.0.1.0.0",
    "category": "Services/Fitness",
    "license": "LGPL-3",
    "author": "ThinBaker",
    "website": "https://thinbaker.com",
    "depends": [
        "base",
        "contacts",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",

        "views/gym_access_views.xml",
        "views/gym_engagement_views.xml",
        "views/gym_customer_health_views.xml",
        "views/gym_churn_trainer_views.xml",
        "views/gym_churn_model_views.xml",

        "views/res_partner_views.xml",

        "views/gym_center_views.xml",

        "views/menu.xml",

        "data/customer_segments.xml",
        "data/gym_demo_data.xml",
        "data/gym_churn_cron.xml",
    ],
    "demo": [
        "demo/demo_partners.xml",
        "demo/demo_access_logs.xml",
        "demo/demo_health_scores.xml",
    ],
    "installable": True,
    "application": True,
}