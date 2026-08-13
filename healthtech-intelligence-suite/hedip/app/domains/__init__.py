"""Domain package registry."""

from app.domains.care_coord import run_care_coord
from app.domains.claims import run_claims
from app.domains.clinical_cds import run_clinical_cds
from app.domains.fraud import run_fraud
from app.domains.knowledge import run_knowledge
from app.domains.pop_health import run_pop_health
from app.domains.prior_auth import run_prior_auth
from app.domains.rcm import run_rcm

DOMAIN_RUNNERS = {
    "prior_auth": run_prior_auth,
    "claims": run_claims,
    "clinical_cds": run_clinical_cds,
    "care_coord": run_care_coord,
    "knowledge": run_knowledge,
    "fraud": run_fraud,
    "pop_health": run_pop_health,
    "rcm": run_rcm,
}
