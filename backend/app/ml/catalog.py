"""Shared reference lists used by the data generator and the entity extractor."""

CATEGORIES = ["payment", "delivery", "product", "refund", "account", "technical"]

PRODUCTS = [
    "SmartWatch X2", "Galaxy Buds Pro", "AirFlow Fan 300", "UltraBook 14", "Nova Phone 12",
    "PowerBank 20K", "HomeCam Mini", "Kettle Pro 1.7L", "Running Shoes Z1", "Mixer Grinder 750W",
    "Noise Cancel Headphones", "Gaming Mouse G5", "LED TV 43 inch", "Air Purifier AP200", "Yoga Mat Plus",
]

CITIES = [
    "Chennai", "Mumbai", "Delhi", "Bengaluru", "Hyderabad",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Kochi",
]

DEPARTMENTS = {
    "payment": "Billing & Payments",
    "delivery": "Logistics",
    "product": "Product Quality",
    "refund": "Refunds & Returns",
    "account": "Account Services",
    "technical": "Technical Support",
}
