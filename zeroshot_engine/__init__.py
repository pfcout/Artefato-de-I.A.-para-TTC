"""zeroshot_engine package — SPIN Zero-Shot adapted version"""

__version__ = "0.1.5"
__author__ = "Lucas Schwarz (adapted by Tele_IA, 2025)"
__email__ = "luc.schwarz@posteo.de"

# ==========================================================
# Import only functional modules that exist in the SPIN build
# ==========================================================

from zeroshot_engine.functions.base import (
    initialize_model,
    generate_prompt,
    get_prompt_id,
    classification_step,
    ensure_numeric,
)

from zeroshot_engine.functions.izsc import (
    set_zeroshot_parameters,
    single_iterative_zeroshot_classification,
    iterative_zeroshot_classification,
)

from zeroshot_engine.functions.validate import validate_combined_predictions

from zeroshot_engine.functions.ollama import (
    setup_ollama,
    check_ollama_updates,
)

from zeroshot_engine.functions.visualization import display_label_flowchart
