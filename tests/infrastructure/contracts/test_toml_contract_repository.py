"""Reading contract definitions from TOML."""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.domain.model.contract import (
    AdapterContract,
    BufferLifetime,
    BusRoleKind,
    ParameterRole,
    WriteMoment,
)
from looper.infrastructure.contracts import ContractDefinitionError, TomlAdapterContractRepository

DEFINITION = """
[adapter_spi_transfer]
tx_data = { role = "input", lifetime = "copied" }
rx_data = { role = "output", written_at = "on_callback" }
callback = { role = "callback" }
"""


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "contract.toml"
    path.write_text(content, encoding="utf-8")
    return path


def _written(tmp_path: Path, content: str) -> AdapterContract:
    """Load a contract from text, which is what most of these tests want."""
    return TomlAdapterContractRepository().load(_write(tmp_path, content))


def test_a_missing_file_yields_an_empty_contract(tmp_path: Path) -> None:
    contract = TomlAdapterContractRepository().load(tmp_path / "absent.toml")

    assert contract.contracted_function_names == ()


def test_parameter_semantics_are_read(tmp_path: Path) -> None:
    contract = TomlAdapterContractRepository().load(_write(tmp_path, DEFINITION))

    transfer = contract.function("adapter_spi_transfer")
    assert transfer.parameter("tx_data").lifetime is BufferLifetime.COPIED
    assert transfer.parameter("rx_data").written_at is WriteMoment.ON_CALLBACK
    assert transfer.parameter("callback").role is ParameterRole.CALLBACK


def test_an_unknown_role_names_the_allowed_values(tmp_path: Path) -> None:
    definition = '[f]\nx = { role = "sideways" }\n'

    with pytest.raises(ContractDefinitionError, match="input_output"):
        TomlAdapterContractRepository().load(_write(tmp_path, definition))


def test_an_unknown_key_is_rejected(tmp_path: Path) -> None:
    definition = '[f]\nx = { role = "input", lifespan = "copied" }\n'

    with pytest.raises(ContractDefinitionError, match="unknown keys: lifespan"):
        TomlAdapterContractRepository().load(_write(tmp_path, definition))


def test_a_lifetime_on_a_callback_is_rejected(tmp_path: Path) -> None:
    definition = '[f]\nx = { role = "callback", lifetime = "borrowed" }\n'

    with pytest.raises(ValueError, match="declares a buffer lifetime"):
        TomlAdapterContractRepository().load(_write(tmp_path, definition))


def test_malformed_toml_names_the_file(tmp_path: Path) -> None:
    with pytest.raises(ContractDefinitionError, match="not valid TOML"):
        TomlAdapterContractRepository().load(_write(tmp_path, "[f\n"))


def test_a_roles_table_says_what_a_function_does(tmp_path: Path) -> None:
    """A role is the difference between generating a stub and behaviour."""
    contract = _written(
        tmp_path,
        """
        [roles.adapter_spi_transfer_blocking]
        kind = "spi.transfer"
        context = "context"
        transmitted = "tx_data"
        received = "rx_data"
        length = "len"
        """,
    )

    role = contract.role("adapter_spi_transfer_blocking")

    assert role is not None
    assert role.kind is BusRoleKind.SPI_TRANSFER
    assert role.named_parameters == ("context", "len", "tx_data", "rx_data")


def test_a_function_without_a_role_has_none(tmp_path: Path) -> None:
    contract = _written(tmp_path, '[adapter_demo]\nbuffer = { role = "input" }\n')

    assert contract.role("adapter_demo") is None
    assert contract.covers("adapter_demo")


def test_the_roles_table_is_not_read_as_a_function(tmp_path: Path) -> None:
    """Its entries are functions, not parameters, and must not be confused."""
    contract = _written(
        tmp_path,
        """
        [roles.adapter_demo]
        kind = "uart.write"
        context = "context"
        data = "data"
        length = "len"
        """,
    )

    assert contract.contracted_function_names == ()


def test_an_unknown_role_kind_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ContractDefinitionError, match="is not one of"):
        _written(tmp_path, '[roles.adapter_demo]\nkind = "pcie.transfer"\n')


def test_an_unknown_role_key_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ContractDefinitionError, match="unknown keys: speed"):
        _written(
            tmp_path,
            '[roles.adapter_demo]\nkind = "uart.write"\nspeed = "fast"\n',
        )


def test_a_role_missing_what_its_kind_needs_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ContractDefinitionError, match="has to name its length"):
        _written(
            tmp_path,
            '[roles.adapter_demo]\nkind = "uart.write"\ncontext = "c"\ndata = "d"\n',
        )
