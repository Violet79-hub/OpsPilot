from pydantic import BaseModel, Field
from app.tools.business import get_order, get_customer, get_support_ticket, calculate_refund
from app.rag.retriever import search_knowledge


class SearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=12)


class OrderInput(BaseModel):
    order_id: str = Field(pattern=r"^NS-\d{4}$")


class CustomerInput(BaseModel):
    customer_id: str = Field(pattern=r"^C\d{3}$")


class TicketInput(BaseModel):
    ticket_id: str = Field(pattern=r"^T\d{3}$")


TOOLS = {
    "search_knowledge": (
        SearchInput,
        search_knowledge,
        "Retrieve policy chunks with source identifiers and vector scores.",
    ),
    "get_order": (OrderInput, get_order, "Read a synthetic order from the database."),
    "get_customer": (
        CustomerInput,
        get_customer,
        "Read a synthetic customer; private email is never returned.",
    ),
    "get_support_ticket": (
        TicketInput,
        get_support_ticket,
        "Read a support ticket and linked references.",
    ),
    "calculate_refund": (
        OrderInput,
        calculate_refund,
        "Calculate a policy-constrained recommendation. No money is moved.",
    ),
}


def invoke(name, args):
    schema, fn, _ = TOOLS[name]
    return fn(**schema.model_validate(args).model_dump())


def schemas():
    return [
        {
            "name": name,
            "description": desc,
            "input_schema": schema.model_json_schema(),
            "read_only": True,
        }
        for name, (schema, _, desc) in TOOLS.items()
    ]
