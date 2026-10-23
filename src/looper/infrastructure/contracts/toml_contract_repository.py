"""Adapter contract repository backed by a TOML definition file."""

from __future__ import annotations

import tomllib
from enum import Enum
from pathlib import Path
from typing import Any

from looper.domain.model.contract import (
    AdapterContract,
    BufferLifetime,
    BusRole,
    BusRoleKind,
    FunctionContract,
    ParameterContract,
    ParameterRole,
    WriteMoment,
)
from looper.domain.repositories import AdapterContractRepository
from looper.infrastructure.contracts.errors import ContractDefinitionError

ROLE_KEY = "role"
LIFETIME_KEY = "lifetime"
WRITTEN_AT_KEY = "written_at"
KNOWN_KEYS = frozenset({ROLE_KEY, LIFETIME_KEY, WRITTEN_AT_KEY})

#: Table holding what functions do, rather than what their parameters mean.
#: Reserved: an adapter function of this name would be indistinguishable
#: from the table, and the loader says so rather than guessing.
ROLES_TABLE = "roles"
KIND_KEY = "kind"
ROLE_KEYS = frozenset(
    {KIND_KEY, "context", "data", "length", "transmitted", "received", "register"}
)


class TomlAdapterContractRepository(AdapterContractRepository):
    """Reads parameter semantics from a TOML file.

    One table per function, one inline table per parameter::

        [adapter_spi_transfer]
        tx_data = { role = "input", lifetime = "copied" }
        rx_data = { role = "output", written_at = "on_callback" }
        callback = { role = "callback" }
    """

    def load(self, contract_path: Path) -> AdapterContract:
        """Read the contract definition, treating a missing file as empty.

        Raises:
            ContractDefinitionError: If the file is malformed.
        """
        if not contract_path.is_file():
            return AdapterContract()
        document = _parse_document(contract_path)
        roles = _read_roles(document.pop(ROLES_TABLE, {}))
        return AdapterContract(
            functions=tuple(_read_function(name, body) for name, body in document.items()),
            roles=roles,
        )


def _parse_document(contract_path: Path) -> dict[str, Any]:
    """Read the TOML document, reporting syntax errors against the file."""
    try:
        return tomllib.loads(contract_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ContractDefinitionError(f"'{contract_path}' is not valid TOML: {error}") from error


def _read_roles(table: object) -> dict[str, BusRole]:
    """Translate the roles table into one role per function."""
    if not isinstance(table, dict):
        raise ContractDefinitionError(f"'{ROLES_TABLE}' must be a table of functions")
    return {name: _read_role(name, body) for name, body in table.items()}


def _read_role(function_name: str, body: object) -> BusRole:
    """Translate one role entry into what the generator needs."""
    context = f"{ROLES_TABLE}.{function_name}"
    if not isinstance(body, dict):
        raise ContractDefinitionError(f"{context} must be a table")
    unknown = sorted(set(body) - ROLE_KEYS)
    if unknown:
        raise ContractDefinitionError(f"{context} has unknown keys: {', '.join(unknown)}")
    try:
        return BusRole(
            kind=_read_enum(BusRoleKind, body.get(KIND_KEY), f"{context}.{KIND_KEY}"),
            context=str(body.get("context", "")),
            data=_optional(body, "data"),
            length=_optional(body, "length"),
            transmitted=_optional(body, "transmitted"),
            received=_optional(body, "received"),
            register=_optional(body, "register"),
        )
    except ValueError as error:
        raise ContractDefinitionError(f"{context}: {error}") from error


def _optional(body: dict[str, Any], key: str) -> str | None:
    """Read one optional parameter name."""
    value = body.get(key)
    return None if value is None else str(value)


def _read_function(function_name: str, body: object) -> FunctionContract:
    """Translate one function table into a function contract."""
    if not isinstance(body, dict):
        raise ContractDefinitionError(f"'{function_name}' must be a table of parameters")
    parameters = tuple(_read_parameter(function_name, name, entry) for name, entry in body.items())
    return FunctionContract(function_name=function_name, parameters=parameters)


def _read_parameter(function_name: str, parameter_name: str, entry: object) -> ParameterContract:
    """Translate one parameter entry into a parameter contract."""
    context = f"{function_name}.{parameter_name}"
    if not isinstance(entry, dict):
        raise ContractDefinitionError(f"{context} must be a table")
    _reject_unknown_keys(context, entry)
    return ParameterContract(
        parameter_name=parameter_name,
        role=_read_enum(ParameterRole, entry.get(ROLE_KEY), f"{context}.{ROLE_KEY}"),
        lifetime=_read_lifetime(entry, context),
        written_at=_read_written_at(entry, context),
    )


def _reject_unknown_keys(context: str, entry: dict[str, Any]) -> None:
    """Reject keys that the contract format does not define."""
    unknown = sorted(set(entry) - KNOWN_KEYS)
    if unknown:
        raise ContractDefinitionError(f"{context} has unknown keys: {', '.join(unknown)}")


def _read_lifetime(entry: dict[str, Any], context: str) -> BufferLifetime:
    """Read the optional buffer lifetime of a parameter."""
    if LIFETIME_KEY not in entry:
        return BufferLifetime.NOT_APPLICABLE
    return _read_enum(BufferLifetime, entry[LIFETIME_KEY], f"{context}.{LIFETIME_KEY}")


def _read_written_at(entry: dict[str, Any], context: str) -> WriteMoment | None:
    """Read the optional write moment of an output parameter."""
    if WRITTEN_AT_KEY not in entry:
        return None
    return _read_enum(WriteMoment, entry[WRITTEN_AT_KEY], f"{context}.{WRITTEN_AT_KEY}")


def _read_enum[EnumT: Enum](enum_type: type[EnumT], raw: object, context: str) -> EnumT:
    """Translate a raw TOML value into one member of an enumeration."""
    try:
        return enum_type(raw)
    except ValueError:
        allowed = ", ".join(str(member.value) for member in enum_type)
        raise ContractDefinitionError(f"{context}: '{raw}' is not one of {allowed}") from None
