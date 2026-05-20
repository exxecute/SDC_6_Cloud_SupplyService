from fastapi import FastAPI, HTTPException
from database import get_connection
from models import ItemCreate, ItemUpdate, ReservationCreate
from logging_config import get_logger

import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import Optional

logger = get_logger("supply-service")
app = FastAPI()

SCHEMA_NAME = "UladzislauMikhayevich"
ITEMS_TABLE = "items"
RESERVATIONS_TABLE = "reservations"


# =========================
# GRAPHQL
# =========================

@strawberry.type
class Item:
    id: int
    name: str
    description: Optional[str]
    total_count: int
    available_count: int
    status: str


@strawberry.type
class Query:

    @strawberry.field
    def get_item(self, id: int) -> Item:
        logger.info(f"GraphQL get item {id}")

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                f"""
                SELECT *
                FROM [{SCHEMA_NAME}].[{ITEMS_TABLE}]
                WHERE id = ?
                """,
                (id,),
            )

            row = cursor.fetchone()

            if not row:
                raise Exception("Item not found")

            columns = [column[0] for column in cursor.description]
            item_data = dict(zip(columns, row))

            return Item(
                id=item_data["id"],
                name=item_data["name"],
                description=item_data["description"],
                total_count=item_data["total_count"],
                available_count=item_data["available_count"],
                status=item_data["status"],
            )

        finally:
            cursor.close()
            conn.close()


schema = strawberry.Schema(query=Query)

graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")


# =========================
# REST API
# =========================

@app.get("/")
def health():
    logger.info("Health check called")
    return {"message": "Supply Service is running"}


@app.get("/setup")
def setup_database():
    logger.info("Setup database")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            IF NOT EXISTS (
                SELECT * FROM sys.schemas
                WHERE name = '{SCHEMA_NAME}'
            )
            BEGIN
                EXEC('CREATE SCHEMA [{SCHEMA_NAME}]')
            END
            """
        )

        cursor.execute(
            f"""
            IF NOT EXISTS (
                SELECT * FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = '{SCHEMA_NAME}'
                AND TABLE_NAME = '{ITEMS_TABLE}'
            )
            BEGIN
                CREATE TABLE [{SCHEMA_NAME}].[{ITEMS_TABLE}] (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    name NVARCHAR(255) NOT NULL,
                    description NVARCHAR(MAX),
                    total_count INT NOT NULL,
                    available_count INT NOT NULL,
                    status NVARCHAR(50) NOT NULL,
                    created_at DATETIME2 DEFAULT GETDATE()
                )
            END
            """
        )

        conn.commit()

        return {"message": "Supply service tables created successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@app.post("/items")
def create_item(item: ItemCreate):
    logger.info("Post item")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            INSERT INTO [{SCHEMA_NAME}].[{ITEMS_TABLE}]
            (name, description, total_count, available_count, status)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                item.name,
                item.description,
                item.total_count,
                item.available_count,
                item.status,
            ),
        )

        item_id = cursor.fetchone()[0]

        conn.commit()

        return {"message": "Item created successfully", "id": item_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@app.get("/items")
def get_items():
    logger.info("Get items")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"SELECT * FROM [{SCHEMA_NAME}].[{ITEMS_TABLE}]"
        )

        rows = cursor.fetchall()

        columns = [column[0] for column in cursor.description]

        return [dict(zip(columns, row)) for row in rows]

    finally:
        cursor.close()
        conn.close()