import os
import datetime
from dotenv import load_dotenv
from peewee import (
    MySQLDatabase,
    Model,
    CharField,
    TextField,
    IntegerField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
)
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()


class AutoConnectingMySQLDatabase(MySQLDatabase):
    def execute_sql(self, sql, params=None, commit=True):
        # Always ensure connection is active before executing SQL
        self.connect(reuse_if_open=True)
        return super().execute_sql(sql, params, commit)


# Initialize db as None - will be set based on environment
if os.getenv("TESTING"):
    db = None  # Will be set by tests
else:
    if os.getenv("MYSQL_HOST") is None:
        raise Exception("MYSQL_HOST is not set")

    # Establish a connection to the MySQL database using environment variables
    db = AutoConnectingMySQLDatabase(
        os.getenv("MYSQL_DATABASE"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
    )
    # Connect only if not in testing mode
    db.connect()


# BaseModel to set the database for all models
class BaseModel(Model):
    class Meta:
        database = db

    @classmethod
    def _check_updates_needed(
        cls,
        existing: Any,
        data: Dict[str, Any],
        exclude_fields: tuple = ("lastUpdated",),
    ) -> bool:
        for key, new_value in data.items():
            if key in exclude_fields:
                continue
            old_value = getattr(existing, key)

            # Handle foreign keys by comparing IDs
            if isinstance(old_value, Model):
                old_value = old_value.get_id()

            if old_value != new_value:
                return True
        return False


# Location table definition
class Location(BaseModel):
    locationId = CharField(primary_key=True)  # Primary key
    description = TextField(null=True)  # Optional description
    dryerCount = IntegerField()  # Number of dryers at the location
    label = CharField()  # Label/name of the location
    machineCount = IntegerField()  # Total number of machines
    washerCount = IntegerField()  # Number of washers
    lastUpdated = DateTimeField(
        default=datetime.datetime.now
    )  # Timestamp of last update


# Room table definition
class Room(BaseModel):
    roomId = CharField(primary_key=True)  # Primary key
    connected = BooleanField()  # Indicates if the room is connected
    description = TextField(null=True)  # Optional room description
    dryerCount = IntegerField()  # Number of dryers in the room
    freePlay = BooleanField()  # Indicates if machines are in free play mode
    label = CharField()  # Label/name of the room
    locationId = ForeignKeyField(
        Location, backref="rooms", column_name="locationId"
    )  # FK to Location
    machineCount = IntegerField()  # Total number of machines
    washerCount = IntegerField()  # Number of washers
    lastUpdated = DateTimeField(
        default=datetime.datetime.now
    )  # Timestamp of last update


# Machine table definition
class Machine(BaseModel):
    available = BooleanField()  # Availability status
    capability_addTime = BooleanField()  # Can add time?
    capability_showAddTimeNotice = BooleanField()  # Show add-time notice?
    capability_showSettings = BooleanField()  # Show settings?
    controllerType = CharField()  # Controller type
    display = TextField(null=True)  # Display text
    doorClosed = BooleanField()  # Is door closed?
    freePlay = BooleanField()  # Is in free play mode?
    groupId = CharField(null=True)  # Optional group ID
    inService = BooleanField(null=True)  # In service or not
    licensePlate = CharField()  # Machine's license plate
    location = ForeignKeyField(
        Location, backref="machines", column_name="locationId"
    )  # FK to Location
    mode = CharField()  # Current mode
    nfcId = CharField()  # NFC identifier
    notAvailableReason = CharField(null=True, default="")  # Reason for unavailability
    opaqueId = CharField()  # Opaque identifier
    qrCodeId = CharField()  # QR code identifier
    roomId = ForeignKeyField(
        Room, backref="machines", column_name="roomId"
    )  # FK to Room
    settings_cycle = CharField()  # Selected cycle setting
    settings_dryerTemp = CharField(null=True)  # Dryer temperature setting
    settings_soil = CharField()  # Soil level setting
    settings_washerTemp = CharField(null=True)  # Optional washer temperature
    stackItems = TextField(null=True)  # Optional stack info
    stickerNumber = IntegerField()  # Sticker number
    timeRemaining = IntegerField()  # Time remaining in current cycle
    type = CharField()  # Machine type (e.g., washer, dryer)
    lastUpdated = DateTimeField(
        default=datetime.datetime.now
    )  # Timestamp of last update
    lastUser = CharField(null=True)  # Optional last user ID or name

    def save(self, *args, **kwargs):
        if self.timeRemaining < 0:
            raise ValueError("timeRemaining cannot be negative")
        return super().save(*args, **kwargs)

    @classmethod
    def create(cls, **query):
        if query.get("timeRemaining", 0) < 0:
            raise ValueError("timeRemaining cannot be negative")
        return super().create(**query)

    @classmethod
    def claim(cls, data: Dict[str, Any]) -> bool:
        opaque_id = data.get("opaqueId")
        existing = cls.get_or_none(cls.opaqueId == opaque_id)

        if existing is None:
            data["lastUpdated"] = datetime.datetime.now()
            data["lastUser"] = "Unknown"
            cls.create(**data)
            return True
        elif data["timeRemaining"] != existing.timeRemaining:
            data["lastUpdated"] = datetime.datetime.now()
            if data["timeRemaining"] - existing.timeRemaining > 5:
                data["lastUser"] = "Unknown"
            cls.update(**data).where(cls.opaqueId == opaque_id).execute()
            return True
        return False


# Discord table definition
class Discord(BaseModel):
    discordId = CharField(primary_key=True)  # Discord user/guild ID
    roomId = CharField()  # Room identifier


# Connect to the database and create tables if they don't exist
if not os.getenv("TESTING"):
    db.create_tables([Location, Room, Machine, Discord], safe=True)
