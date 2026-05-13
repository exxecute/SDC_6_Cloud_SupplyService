from fastapi import FastAPI, HTTPException
from database import get_connection
from models import ItemCreate, ItemUpdate, ReservationCreate
from fastapi import HTTPException
from logging_config import get_logger

logger = get_logger("supply-service")
app = FastAPI()

SCHEMA_NAME = "UladzislauMikhayevich"
ITEMS_TABLE = "items"
RESERVATIONS_TABLE = "reservations"


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

        cursor.execute(
            f"""
            IF NOT EXISTS (
                SELECT * FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = '{SCHEMA_NAME}'
                AND TABLE_NAME = '{RESERVATIONS_TABLE}'
            )
            BEGIN
                CREATE TABLE [{SCHEMA_NAME}].[{RESERVATIONS_TABLE}] (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    item_id INT NOT NULL,
                    rental_id INT NOT NULL,
                    reserved_count INT NOT NULL,
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


@app.get("/items/{id}")
def get_item(id: int):
    logger.info("Get item")
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
            raise HTTPException(status_code=404, detail="Item not found")

        columns = [column[0] for column in cursor.description]

        return dict(zip(columns, row))

    finally:
        cursor.close()
        conn.close()


@app.put("/items/{id}")
def update_item(id: int, item: ItemUpdate):
    logger.info("Put item")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        update_fields = []
        values = []

        item_data = item.dict(exclude_unset=True)

        for key, value in item_data.items():
            update_fields.append(f"{key} = ?")
            values.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(id)

        query = f"""
        UPDATE [{SCHEMA_NAME}].[{ITEMS_TABLE}]
        SET {", ".join(update_fields)}
        WHERE id = ?
        """

        cursor.execute(query, values)
        conn.commit()

        return {"message": "Item updated successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@app.delete("/items/{id}")
def delete_item(id: int):
    logger.info("Delete item")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            DELETE FROM [{SCHEMA_NAME}].[{ITEMS_TABLE}]
            WHERE id = ?
            """,
            (id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")

        conn.commit()
        return {"message": "Item deleted successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@app.post("/items/{id}/reserve")
def reserve_item(id: int, reservation: ReservationCreate):
    logger.info(f"Post item reserve {id}")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            SELECT available_count
            FROM [{SCHEMA_NAME}].[{ITEMS_TABLE}]
            WHERE id = ?
            """,
            (id,),
        )

        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Item not found")

        available_count = row[0]

        if available_count < reservation.reserved_count:
            raise HTTPException(
                status_code=400,
                detail="Not enough items available",
            )

        new_available = available_count - reservation.reserved_count

        cursor.execute(
            f"""
            UPDATE [{SCHEMA_NAME}].[{ITEMS_TABLE}]
            SET available_count = ?
            WHERE id = ?
            """,
            (new_available, id),
        )

        cursor.execute(
            f"""
            INSERT INTO [{SCHEMA_NAME}].[{RESERVATIONS_TABLE}]
            (item_id, rental_id, reserved_count, status)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?)
            """,
            (id, reservation.rental_id,
             reservation.reserved_count, "reserved"),
        )

        reservation_id = cursor.fetchone()[0]

        conn.commit()

        return {
            "message": "Item reserved successfully",
            "reservation_id": reservation_id,
            "available_count": new_available,
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@app.post("/items/{id}/release")
def release_item(id: int, reservation: ReservationCreate):
    logger.info(f"Item release {id}")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            SELECT id, reserved_count, status
            FROM [{SCHEMA_NAME}].[{RESERVATIONS_TABLE}]
            WHERE item_id = ?
            AND rental_id = ?
            AND status = 'reserved'
            """,
            (id, reservation.rental_id),
        )

        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Active reservation not found",
            )

        reservation_id = row[0]
        reserved_count = row[1]

        cursor.execute(
            f"""
            SELECT available_count
            FROM [{SCHEMA_NAME}].[{ITEMS_TABLE}]
            WHERE id = ?
            """,
            (id,),
        )

        item = cursor.fetchone()
        available_count = item[0]

        new_available = available_count + reserved_count

        cursor.execute(
            f"""
            UPDATE [{SCHEMA_NAME}].[{ITEMS_TABLE}]
            SET available_count = ?
            WHERE id = ?
            """,
            (new_available, id),
        )

        cursor.execute(
            f"""
            UPDATE [{SCHEMA_NAME}].[{RESERVATIONS_TABLE}]
            SET status = 'released'
            WHERE id = ?
            """,
            (reservation_id,),
        )

        conn.commit()

        return {
            "message": "Reservation released successfully",
            "available_count": new_available,
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()
