"""Build the training dataset and the demo complaint stream.

Outputs (data/processed/):
  train.csv / val.csv / test.csv  - labelled complaints (Bitext + synthetic)
  live_complaints.csv             - 60-day complaint stream with an injected spike
                                     and near-duplicates, used to seed the app

Synthetic train/test are split by *template*, so test templates are never seen
during training (avoids measuring template memorisation).
"""
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.catalog import CITIES, PRODUCTS  # noqa: E402

RAW = ROOT / "data" / "raw" / "bitext.csv"
OUT = ROOT / "data" / "processed"
rng = random.Random(42)

# ---------------------------------------------------------------- Bitext ----
BITEXT_MAP = {
    "payment_issue": "payment", "check_payment_methods": "payment",
    "check_invoice": "payment", "get_invoice": "payment", "check_cancellation_fee": "payment",
    "delivery_period": "delivery", "delivery_options": "delivery", "track_order": "delivery",
    "change_shipping_address": "delivery", "set_up_shipping_address": "delivery",
    "get_refund": "refund", "track_refund": "refund", "check_refund_policy": "refund",
    "create_account": "account", "delete_account": "account", "edit_account": "account",
    "switch_account": "account", "recover_password": "account",
    "registration_problems": "technical",
}
BITEXT_PER_CLASS = 600


def order_id():
    return f"ORD-{rng.randint(100000, 999999)}"


def fill_bitext(text):
    repl = {
        "{{Order Number}}": order_id, "{{Person Name}}": lambda: rng.choice(["Ravi", "Priya", "Arjun", "Meena"]),
        "{{Refund Amount}}": lambda: str(rng.randint(200, 9000)), "{{Currency Symbol}}": lambda: "₹",
        "{{Delivery City}}": lambda: rng.choice(CITIES), "{{Delivery Country}}": lambda: "India",
        "{{Account Type}}": lambda: rng.choice(["premium", "standard"]),
        "{{Account Category}}": lambda: rng.choice(["business", "personal"]),
        "{{Invoice Number}}": lambda: f"INV-{rng.randint(1000, 9999)}",
    }
    for k, f in repl.items():
        while k in text:
            text = text.replace(k, f(), 1)
    return re.sub(r"\{\{[^}]+\}\}", "", text).strip()


BITEXT_URL = ("https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/"
              "resolve/main/Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv")


def load_bitext():
    if not RAW.exists():
        import urllib.request
        RAW.parent.mkdir(parents=True, exist_ok=True)
        print("downloading Bitext dataset...")
        urllib.request.urlretrieve(BITEXT_URL, RAW)
    df = pd.read_csv(RAW)
    df = df[df.intent.isin(BITEXT_MAP)].copy()
    df["category"] = df.intent.map(BITEXT_MAP)
    df = pd.concat([g.sample(min(len(g), BITEXT_PER_CLASS), random_state=42)
                    for _, g in df.groupby("category")])
    df["text"] = df.instruction.map(fill_bitext)
    df["source"] = "bitext"
    df["template_id"] = "bitext"
    df["sentiment_label"] = ""  # Bitext has no sentiment labels
    return df[["text", "category", "source", "template_id", "sentiment_label"]]


# ------------------------------------------------------------- Synthetic ----
# {o}=order id {p}=product {a}=amount {c}=city {d}=date
TEMPLATES = {
    "payment": [
        "I was charged twice for order {o}. ₹{a} got debited two times from my card on {d}.",
        "Payment of ₹{a} failed but money was deducted from my bank account for {o}.",
        "My UPI payment for the {p} went through on {d} but the order {o} still shows payment pending.",
        "There is an unauthorized charge of ₹{a} on my credit card from your site.",
        "The invoice for order {o} shows ₹{a} which is more than the price I saw at checkout.",
        "EMI option was selected for the {p} but the full amount ₹{a} was charged.",
        "Coupon discount was not applied and I paid ₹{a} extra for order {o}.",
        "My card got declined three times while paying for the {p}, yet the bank shows a hold of ₹{a}.",
        "I got billed ₹{a} for a subscription I never signed up for.",
        "Cash on delivery charges of ₹{a} were added to {o} even though I paid online.",
        "The payment gateway timed out and I was debited ₹{a} for {o} with no confirmation.",
        "Why was GST charged twice on my invoice for {o}? Total came to ₹{a}.",
    ],
    "delivery": [
        "My order {o} was supposed to arrive on {d} but it still has not been delivered to {c}.",
        "The tracking for {o} has been stuck at the {c} hub for a week.",
        "The courier marked {o} as delivered on {d} but I never received the {p}.",
        "Delivery of my {p} keeps getting rescheduled. I live in {c} and nobody shows up.",
        "The delivery agent was rude and refused to come to my floor in {c}.",
        "My parcel {o} was delivered to the wrong address in {c}.",
        "The box for {o} arrived crushed and open, delivered on {d}.",
        "Order {o} shows out for delivery since {d} but nothing has arrived in {c}.",
        "Expected delivery date for the {p} keeps changing, it is now 10 days late.",
        "I paid for express shipping for {o} but it took over a week to reach {c}.",
        "Courier partner says my address in {c} is unserviceable after I already paid for {o}.",
        "Only one of the two items in {o} was delivered, the {p} is missing.",
    ],
    "product": [
        "The {p} I received in order {o} stopped working after two days.",
        "The battery of my {p} drains within an hour, this is a defective unit.",
        "I received a damaged {p} with a cracked screen.",
        "The {p} is not the same as shown in the pictures, the quality is very poor.",
        "My {p} is overheating badly and smells like burning plastic.",
        "The {p} from order {o} came with missing accessories and no charger.",
        "The {p} makes a loud noise when switched on, clearly a manufacturing defect.",
        "Received the wrong colour and size of {p} in {o}.",
        "The {p} has stopped charging completely within the warranty period.",
        "The stitching of the {p} came apart after one use.",
        "The {p} I bought on {d} keeps restarting on its own.",
        "The {p} was expired/used when it arrived, the seal was broken.",
    ],
    "refund": [
        "I returned the {p} on {d} but have not received my refund of ₹{a} yet.",
        "My refund for order {o} was approved two weeks ago but the money has not reached my account.",
        "I cancelled {o} before dispatch and still have not got the ₹{a} back.",
        "Refund of ₹{a} was credited as store wallet balance instead of to my bank account.",
        "Only ₹{a} was refunded for {o} instead of the full amount.",
        "The pickup for my return of the {p} never happened so the refund is stuck.",
        "Your support promised a refund for {o} in 5 days, it has been a month.",
        "The refund for the defective {p} was rejected without any reason.",
        "I want a full refund of ₹{a} for {o}, the item was never delivered.",
        "Return request for the {p} keeps failing on the app so I cannot get my money back.",
        "Refund status for {o} shows processed on {d} but my bank has nothing.",
        "You deducted a restocking fee of ₹{a} from my refund which was never mentioned.",
    ],
    "account": [
        "I cannot log in to my account, it says my password is wrong even after resetting it.",
        "My account was locked after I tried to update my phone number.",
        "Someone else logged into my account and placed order {o} without my permission.",
        "I am not receiving the OTP to verify my account.",
        "I want to delete my account and all my personal data but there is no option.",
        "My email address was changed on my account without my knowledge on {d}.",
        "My saved addresses and order history disappeared from my account.",
        "The account verification keeps failing when I upload my ID.",
        "My loyalty points vanished from my account after {d}.",
        "I keep getting logged out of my account every few minutes.",
        "Two accounts got merged and now I see someone else's orders.",
        "I cannot change the registered mobile number on my account.",
    ],
    "technical": [
        "The app crashes every time I open the cart page.",
        "The website shows error 500 when I try to checkout.",
        "The search on the app returns no results for any product.",
        "Push notifications from the app are not working since the last update.",
        "The checkout button is greyed out and I cannot place order {o}.",
        "The app is extremely slow and keeps freezing on Android.",
        "Images are not loading on the product pages in the iOS app.",
        "The page goes blank after I apply a coupon code.",
        "The app logs me out and shows a network error even on good wifi.",
        "Live chat support widget is not loading on the website.",
        "The app update on {d} broke the order tracking screen.",
        "I cannot upload photos for my product review, the upload keeps failing.",
    ],
}
TEST_TEMPLATES = {9, 10, 11}   # held out for test
VAL_TEMPLATES = {8}            # held out for validation

TONES = {
    # label: (prefixes, suffixes)
    "positive": (["Hi team, I usually love your service.", "Thanks for the quick support last time."],
                 ["Hope you can sort this out, thanks!", "Appreciate your help."]),
    "neutral": (["Hello,", "Hi,", ""],
                ["Please look into it.", "Kindly check.", ""]),
    "negative": (["I am disappointed.", "This is frustrating.", "Not happy with this."],
                 ["Please fix this soon.", "This is poor service.", "Very disappointing."]),
    "highly_negative": (["This is absolutely unacceptable!!!", "WORST EXPERIENCE EVER.", "I am extremely angry."],
                        ["I will file a consumer complaint and never shop here again!",
                         "Fix this TODAY or I am going to my lawyer.", "Totally disgusted with your service!!"]),
}
TONE_WEIGHTS = {"positive": 0.08, "neutral": 0.32, "negative": 0.38, "highly_negative": 0.22}
URGENT = ["This is urgent.", "I need this resolved immediately.", "Please respond ASAP."]


def rand_date(base=None):
    d = (base or datetime(2026, 11, 1)) - timedelta(days=rng.randint(1, 20))
    return d.strftime("%d %b %Y")


def make_complaint(cat, t_idx, tone=None, slots=None, product=None, city=None):
    tone = tone or rng.choices(list(TONE_WEIGHTS), weights=TONE_WEIGHTS.values())[0]
    s = slots or {"o": order_id(), "p": product or rng.choice(PRODUCTS), "a": str(rng.randint(199, 49999)),
                  "c": city or rng.choice(CITIES), "d": rand_date()}
    body = TEMPLATES[cat][t_idx].format(**s)
    pre, suf = TONES[tone]
    parts = [rng.choice(pre), body, rng.choice(suf)]
    if rng.random() < 0.2:
        parts.append(rng.choice(URGENT))
    text = " ".join(p for p in parts if p)
    used = lambda k: "{" + k + "}" in TEMPLATES[cat][t_idx]  # noqa: E731
    return {
        "text": text, "category": cat, "source": "synthetic", "template_id": f"{cat}_{t_idx}",
        "sentiment_label": tone,
        "order_id": s["o"] if used("o") else "", "product": s["p"] if used("p") else "",
        "amount": s["a"] if used("a") else "", "location": s["c"] if used("c") else "",
    }


def build_labelled():
    rows = []
    for cat, temps in TEMPLATES.items():
        for t in range(len(temps)):
            for _ in range(60):
                rows.append(make_complaint(cat, t))
    syn = pd.DataFrame(rows)
    t_num = syn.template_id.str.split("_").str[-1].astype(int)
    split = t_num.map(lambda t: "test" if t in TEST_TEMPLATES else "val" if t in VAL_TEMPLATES else "train")

    bit = load_bitext()
    b_split = pd.Series(rng.choices(["train", "val", "test"], weights=[0.7, 0.15, 0.15], k=len(bit)), index=bit.index)

    for name in ["train", "val", "test"]:
        part = pd.concat([syn[split == name], bit[b_split == name]], ignore_index=True)
        part = part.sample(frac=1, random_state=42)
        part.to_csv(OUT / f"{name}.csv", index=False)
        print(name, len(part), part.category.value_counts().to_dict())


# ------------------------------------------------------------ Live stream ---
def build_live(days=60, per_day=(12, 22)):
    """Complaint stream ending 2026-11-07 with:
      - a delivery spike in Chennai over the last 3 days
      - a product spike for 'SmartWatch X2' (battery/overheating) over the last 4 days
      - ~5% near-duplicate complaints (same customer re-submitting)
    Each complaint has a random customer ID from a pool of 1000, so many customers
    complain more than once about different issues ("same customer" alone is not a duplicate).
    """
    customers = [f"CUST-{i:05d}" for i in range(1, 1001)]
    end = datetime(2026, 11, 7)
    rows = []
    for d in range(days):
        day = end - timedelta(days=days - 1 - d)
        n = rng.randint(*per_day)
        for _ in range(n):
            cat = rng.choice(list(TEMPLATES))
            rows.append({**make_complaint(cat, rng.randrange(12)), "created_at": day + timedelta(minutes=rng.randint(0, 1439))})
        if d >= days - 3:  # Chennai delivery spike
            for _ in range(rng.randint(14, 20)):
                r = make_complaint("delivery", rng.choice([0, 1, 7]), city="Chennai")
                rows.append({**r, "created_at": day + timedelta(minutes=rng.randint(0, 1439))})
        if d >= days - 4:  # SmartWatch X2 defect spike
            for _ in range(rng.randint(8, 12)):
                r = make_complaint("product", rng.choice([1, 4, 8]), product="SmartWatch X2")
                rows.append({**r, "created_at": day + timedelta(minutes=rng.randint(0, 1439))})

    df = pd.DataFrame(rows).sort_values("created_at").reset_index(drop=True)
    df["customer"] = [rng.choice(customers) for _ in range(len(df))]
    df["duplicate_of"] = -1
    # Near-duplicates: same customer complains again 0-2 days later, reworded.
    dups = []
    for i in rng.sample(range(len(df)), k=int(0.05 * len(df))):
        src = df.loc[i]
        text = rng.choice(["Following up again: ", "Second time writing about this. ", "Still no response! "]) + src.text
        dups.append({**src.to_dict(), "text": text, "duplicate_of": i,
                     "created_at": src.created_at + timedelta(hours=rng.randint(2, 48))})
    df = pd.concat([df, pd.DataFrame(dups)], ignore_index=True)
    df = df[df.created_at <= end + timedelta(days=1)]
    df.index.name = "row_id"
    df.to_csv(OUT / "live_complaints.csv")
    print("live", len(df), "duplicates", (df.duplicate_of >= 0).sum())


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_labelled()
    build_live()
