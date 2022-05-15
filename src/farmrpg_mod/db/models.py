import datetime
import re
import types
import typing

import attrs
import orm
import orm.fields
import orm.models

from .conn import registry

_C = typing.TypeVar("_C", bound=type)


CAMEL_TO_SNAKE_RE = re.compile(r"(?<!^)(?=[A-Z])")


PYTHON_TYPES_TO_ORM_FIELDS = {
    str: orm.Text,
    int: orm.Integer,
    bool: orm.Boolean,
    datetime.datetime: orm.DateTime,
}


def attribute_to_field(attr: attrs.Attribute, **kwargs) -> orm.fields.ModelField:
    primary_type = attr.type
    nullable = False
    if isinstance(primary_type, types.UnionType):
        union_types = [
            t
            for t in typing.get_args(primary_type)
            if t is not types.NoneType  # noqa: E721
        ]
        if len(union_types) == 1:
            primary_type = union_types[0]
            nullable = True
    # Fill in some arguments based on attrs data.
    if attr.default is not attrs.NOTHING:
        kwargs["default"] = attr.default
    kwargs["allow_null"] = nullable

    # Build the field object.
    orm_field_type = PYTHON_TYPES_TO_ORM_FIELDS.get(primary_type)
    if orm_field_type is None:
        raise ValueError(f"Unable to find field type for {attr}")
    return orm_field_type(**kwargs)


def orm_model_for_class(
    cls: type, table_name: str, primary_key: str, fields: list[str]
) -> type:
    attributes = attrs.fields_dict(attrs.resolve_types(cls))
    orm_fields = {}
    orm_fields[primary_key] = attribute_to_field(
        attributes[primary_key], primary_key=True
    )
    orm_fields["json_data"] = orm.JSON()
    for f in fields:
        unique = False
        if f.startswith("!"):
            unique = True
            f = f[1:]
        orm_fields[f] = attribute_to_field(attributes[f], index=True, unique=unique)
    return type(
        cls.__name__,
        (orm.Model,),
        {
            "tablename": table_name,
            "registry": registry,
            "fields": orm_fields,
        },
    )


class AttrsQuerySet(typing.Generic[_C], orm.models.QuerySet):
    # Hack to disable the accessor stuff since we're manually specifying
    # the model class.
    def __get__(self, instance, owner):
        return self

    async def create(self, _obj: typing.Any = None, **kwargs):
        if _obj is not None:
            kwargs = attrs.asdict(_obj) | kwargs
        return super().create(**kwargs)


def _attrs_model(
    cls: _C, *, primary_key: str, fields: list[str], table_name: str | None
) -> _C:
    if table_name is None:
        table_name = CAMEL_TO_SNAKE_RE.sub("_", cls.__name__).lower()
    orm_model = orm_model_for_class(
        cls, table_name=table_name, primary_key=primary_key, fields=fields
    )
    setattr(cls, "orm_model", orm_model)
    setattr(cls, "objects", AttrsQuerySet(model_cls=orm_model))
    return cls


@typing.overload
def attrs_model(
    *, primary_key: str = "id", fields: list[str] = [], table_name: str | None = None
) -> typing.Callable[[_C], _C]:
    ...


@typing.overload
def attrs_model(cls: _C) -> _C:
    ...


def attrs_model(
    cls: _C | None = None,
    *,
    primary_key: str = "id",
    fields: list[str] = [],
    table_name: str | None = None,
) -> typing.Callable[[_C], _C] | _C:
    if cls is None:

        def wrapper(cls: _C) -> _C:
            return _attrs_model(
                cls, primary_key=primary_key, fields=fields, table_name=table_name
            )

        return wrapper
    else:
        return _attrs_model(
            cls, primary_key=primary_key, fields=fields, table_name=table_name
        )
