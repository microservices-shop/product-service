from enum import Enum


class AttributeType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"
    ARRAY = "array"


class ProductStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
