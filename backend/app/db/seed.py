from datetime import date, timedelta
from app.config import AS_OF, DATA
from app.db.models import Customer, Order, SupportTicket
from app.db.repository import Session
from app.rag.ingestion import ingest


def seed():
    with Session.begin() as s:
        if not s.get(Customer, "C001"):
            for id_, name, tier, risk in [
                ("C001", "Emily Chen", "Gold", "low"),
                ("C002", "Alex Rivera", "Standard", "low"),
                ("C003", "Sam Patel", "Silver", "high"),
                ("C004", "Jordan Lee", "Gold", "medium"),
            ]:
                s.add(
                    Customer(
                        id=id_,
                        name=name,
                        email=id_.lower() + "@example.invalid",
                        tier=tier,
                        risk_level=risk,
                        account_created="2025-01-01",
                        country="AU",
                    )
                )
            s.flush()
            specs = [
                (1042, "C001", 18, 899, "defective", "physical", "delivered"),
                (1043, "C002", 20, 100, "unopened", "physical", "delivered"),
                (1044, "C002", 20, 100, "opened", "physical", "delivered"),
                (1045, "C002", 40, 200, "unopened", "physical", "delivered"),
                (1046, "C001", 40, 200, "unopened", "physical", "delivered"),
                (1047, "C002", 60, 700, "defective", "physical", "delivered"),
                (1048, "C002", 400, 700, "defective", "physical", "delivered"),
                (1049, "C003", 10, 150, "unopened", "physical", "delivered"),
                (1050, "C002", 5, 50, "unopened", "digital", "delivered"),
                (1051, "C002", 3, 100, "unopened", "physical", "in_transit"),
                (1052, "C001", 10, 2000, "unopened", "physical", "delivered"),
                (1053, "C002", 5, 30, "unused", "subscription", "delivered"),
                (1054, "C002", 8, 30, "unused", "subscription", "delivered"),
                (1055, "C002", 5, 30, "used", "subscription", "delivered"),
                (1056, "C002", 30, 100, "unopened", "physical", "delivered"),
                (1057, "C002", 31, 100, "unopened", "physical", "delivered"),
                (1058, "C001", 45, 100, "unopened", "physical", "delivered"),
                (1059, "C001", 46, 100, "unopened", "physical", "delivered"),
                (1060, "C002", 365, 100, "defective", "physical", "delivered"),
                (1061, "C002", 366, 100, "defective", "physical", "delivered"),
                (1062, "C002", 10, 100, "misuse", "physical", "delivered"),
                (1063, "C004", 15, 100, "unopened", "physical", "delivered"),
                (1064, "C002", 7, 30, "unused", "subscription", "delivered"),
            ]
            for num, cid, days, amount, condition, category, status in specs:
                d = (date.fromisoformat(AS_OF) - timedelta(days=days)).isoformat()
                s.add(
                    Order(
                        id=f"NS-{num}",
                        customer_id=cid,
                        product="Laptop" if amount >= 700 else "Northstar product",
                        amount=amount,
                        purchase_date=d,
                        delivery_date=d if status == "delivered" else None,
                        status=status,
                        condition=condition,
                        category=category,
                    )
                )
            s.flush()
            s.add(
                SupportTicket(
                    id="T001",
                    customer_id="C001",
                    order_id="NS-1042",
                    category="refund",
                    status="open",
                    description="Verified hardware defect. Customer requests a refund.",
                )
            )
    for p in sorted((DATA / "policies").glob("*.md")):
        ingest(p.name, p.read_bytes(), trusted=True, document_id=p.stem)
