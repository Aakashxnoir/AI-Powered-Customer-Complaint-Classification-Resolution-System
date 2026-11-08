# Dataset

## Sources

| Part | Source | Licence | Used for |
|---|---|---|---|
| Bitext customer support | [bitext/Bitext-customer-support-llm-chatbot-training-dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset) (Hugging Face, 26,872 rows) | CDLA-Sharing-1.0 | Real-style support requests for 5 of the 6 categories |
| Synthetic complaints | `ml/generate_data.py` (this repo, seed 42) | Same as this repo | All 6 categories, entity ground truth, sentiment tone labels, demo stream |
| Support playbooks | `data/kb/*.md` (written for this project) | Same as this repo | "Approved guidance" retrieved for response drafting |

`data/raw/bitext.csv` is not committed. `ml/generate_data.py` downloads it on first run.

## Preprocessing

**Bitext.** Only intents that map to a target category are kept. The rest (cancel order, newsletter, reviews and so on) are dropped.

| Category | Bitext intents |
|---|---|
| payment | payment_issue, check_payment_methods, check_invoice, get_invoice, check_cancellation_fee |
| delivery | delivery_period, delivery_options, track_order, change_shipping_address, set_up_shipping_address |
| refund | get_refund, track_refund, check_refund_policy |
| account | create_account, delete_account, edit_account, switch_account, recover_password |
| technical | registration_problems |

Each category is capped at 600 rows. Placeholders such as `{{Order Number}}` and `{{Refund Amount}}` are filled with realistic values (`ORD-123456`, `₹4,500`, Indian cities).

**Synthetic.** There are 12 complaint templates per category (72 in total). Slots are filled with order ID, product (15-item catalogue), amount, city and date. Each complaint is wrapped in one of 4 tones: positive, neutral, negative, highly negative. About 20% also get an urgency phrase. The tone is stored as the sentiment label. The slot values are stored as entity ground truth.

**Text normalisation at intake** (`backend/app/ml/preprocess.py`) does this:
- unescapes HTML and strips tags, URLs and zero-width characters
- collapses whitespace
- rejects empty text, text under 10 or over 5000 characters, and text with no letters

CSV uploads also skip exact repeat rows.

## Splits

| Split | Rows | Rule |
|---|---|---|
| train | 4,965 | synthetic templates 0-7, plus 70% of Bitext (random) |
| val | 818 | synthetic template 8, plus 15% of Bitext |
| test | 1,537 | synthetic templates 9-11, plus 15% of Bitext |

Synthetic data is split **by template**, so the test set holds sentence patterns the model never saw. The validation split is used only to choose the regularisation strength `C`. The final model is refit on train and val together.

## Demo stream (`live_complaints.csv`)

1,194 complaints spread over 60 days (8 Sep to 7 Nov 2026), each with a customer ID. Three effects are injected:
- **Delivery spike in Chennai.** 14-20 extra complaints per day over the last 3 days.
- **Defect spike for SmartWatch X2.** 8-12 extra battery or overheating complaints per day over the last 4 days.
- **55 near-duplicates.** The same customer re-submits the same complaint 2-48 hours later, with a prefix such as "Still no response!". The `duplicate_of` column is the ground truth.

## Regenerate

```bash
backend/.venv/bin/python ml/generate_data.py
```
