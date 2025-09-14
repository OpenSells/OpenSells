# Plan limits configuration

X_FREE_SEARCHES = 4
X_STARTER_LEADS = 150
X_PRO_LEADS = 600
X_BUSINESS_LEADS = 2000

PLAN_LIMITS = {
    "free": {"searches_per_month": X_FREE_SEARCHES, "leads_per_month": 0},
    "starter": {"leads_per_month": X_STARTER_LEADS, "searches_per_month": None},
    "pro": {"leads_per_month": X_PRO_LEADS, "searches_per_month": None},
    "business": {"leads_per_month": X_BUSINESS_LEADS, "searches_per_month": None},
}
