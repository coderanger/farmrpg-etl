import datetime
import re
import types
import typing

import attrs
import cattrs
import orm
import orm.fields
import orm.models
import sqlalchemy
import typesystem

from .conn import registry

_C = typing.TypeVar("_C", bound=type)
_T = typing.TypeVar("_T")


CAMEL_TO_SNAKE_RE = re.compile(r"(?<!^)(?=[A-Z])")


class AnyLengthString(orm.fields.ModelField):
    def get_validator(self, **kwargs) -> typesystem.Field:
        return typesystem.String(**kwargs)

    def get_column_type(self):
        return sqlalchemy.String()


class DateTimeWithTimestamp(orm.fields.DateTime):
    def get_column_type(self):
        return sqlalchemy.TIMESTAMP(timezone=True)


PYTHON_TYPES_TO_ORM_FIELDS = {
    str: AnyLengthString,
    int: orm.Integer,
    bool: orm.Boolean,
    datetime.datetime: DateTimeWithTimestamp,
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
    cls: type, table_name: str, primary_key: str | None, index: dict[str, bool]
) -> type:
    attributes = attrs.fields_dict(attrs.resolve_types(cls))
    orm_fields = {}
    if primary_key is None:
        orm_fields["rowid"] = orm.Integer(primary_key=True)
    else:
        orm_fields[primary_key] = attribute_to_field(
            attributes[primary_key],
            primary_key=True,
            index=True,
        )
    for name, attr in attributes.items():
        if primary_key is not None and name == primary_key:
            continue
        orm_fields[name] = attribute_to_field(
            attributes[name], index=name in index, unique=index.get(name, False)
        )

    # Hacked copy of orm.Model._from_row to construct our attrs object instead.
    def _from_row(inner_cls, row, select_related=[]):
        item = {}

        # Instantiate any child instances first.
        for related in select_related:
            if "__" in related:
                first_part, remainder = related.split("__", 1)
                model_cls = inner_cls.fields[first_part].target
                item[first_part] = model_cls._from_row(row, select_related=[remainder])
            else:
                model_cls = inner_cls.fields[related].target
                item[related] = model_cls._from_row(row)

        # Pull out the regular column values.
        for column in inner_cls.table.columns:
            if column.name not in item:
                item[column.name] = row[column]

        # Remove rowid in most cases.
        if primary_key is None and "rowid" not in attributes:
            item.pop("rowid", None)

        return cattrs.structure(item, cls)

    return type(
        cls.__name__,
        (orm.Model,),
        {
            "tablename": table_name,
            "registry": registry,
            "fields": orm_fields,
            "_from_row": classmethod(_from_row),
        },
    )


class AttrsQuerySet(typing.Generic[_T], orm.models.QuerySet):
    def __get__(self, instance, owner):
        return self.__class__(model_cls=owner.orm_model)

    def create(self, _obj: _T | None = None, /, **kwargs):
        if _obj is not None:
            kwargs = cattrs.unstructure(_obj) | kwargs
        return super().create(**kwargs)


def _attrs_model(
    cls: _C, *, primary_key: str | None, index: list[str], table_name: str | None
) -> _C:
    if table_name is None:
        table_name = CAMEL_TO_SNAKE_RE.sub("_", cls.__name__).lower()
    # Parse index requests.
    index_dict = {}
    for f in index:
        unique = False
        if f.startswith("!"):
            unique = True
            f = f[1:]
        index_dict[f] = unique
    orm_model = orm_model_for_class(
        cls, table_name=table_name, primary_key=primary_key, index=index_dict
    )
    setattr(cls, "orm_model", orm_model)
    return cls


@typing.overload
def attrs_model(
    *,
    primary_key: str | None = None,
    index: list[str] = [],
    table_name: str | None = None,
) -> typing.Callable[[_C], _C]:
    ...


@typing.overload
def attrs_model(cls: _C) -> _C:
    ...


def attrs_model(
    cls: _C | None = None,
    *,
    primary_key: str | None = None,
    index: list[str] = [],
    table_name: str | None = None,
) -> typing.Callable[[_C], _C] | _C:
    if cls is None:

        def wrapper(cls: _C) -> _C:
            return _attrs_model(
                cls, primary_key=primary_key, index=index, table_name=table_name
            )

        return wrapper
    else:
        return _attrs_model(
            cls, primary_key=primary_key, index=index, table_name=table_name
        )


def objects(cls: typing.Type[_T]) -> AttrsQuerySet[_T]:
    return AttrsQuerySet(model_cls=cls.orm_model)  # type: ignore
