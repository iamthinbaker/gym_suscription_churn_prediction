{
    "name": "GymBaker",
    "summary": "Herramienta de gestión de GymBaker con IA para predecir abandono de cliente",
    "icon": "/gym_backoffice/static/description/icon.svg",
    "version": "19.0.1.0.0",
    "category": "Services/Fitness",
    "license": "LGPL-3",
    "author": "ThinBaker",
    "website": "https://thinbaker.com",
    "depends": [
        "base",
        "contacts",
        "mail",
        "portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",

        "views/gym_access_views.xml",
        "views/gym_engagement_views.xml",
        "views/gym_customer_health_views.xml",
        "views/gym_churn_trainer_views.xml",
        "views/gym_churn_survival_trainer_views.xml",
        "views/gym_class_booking_views.xml",
        "views/gym_class_views.xml",
        "views/gym_promotion_views.xml",

        "views/res_partner_views.xml",

        "views/gym_center_views.xml",

        "views/portal_templates.xml",

        "views/menu.xml",

        "data/customer_segments.xml",
        "data/gym_demo_data.xml",
        "data/gym_churn_cron.xml",
    ],
    "demo": [
        "demo/demo_partners.xml",
        "demo/demo_access_logs.xml",
        "demo/demo_health_scores.xml",
        "demo/demo_classes.xml",
        "demo/demo_promotions.xml",
        "demo/demo_portal_users.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "gym_backoffice/static/src/css/portal_gym.css",
        ],
    },
    "installable": True,
    "application": True,
}