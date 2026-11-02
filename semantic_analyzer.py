"""
Semantic analysis for the DFA Language Compiler.

Expected input (dictionary):
{
    "name": "M",
    "states": ["q0", "q1"],
    "alphabet": ["0", "1"],
    "start_state": "q0",
    "final_states": ["q1"],
    "transitions": [
        {"from": "q0", "symbol": "0", "to": "q1"},
        {"from": "q0", "symbol": "1", "to": "q0"}
    ]
}

Transitions may also be supplied as tuples/lists:
    ("q0", "0", "q1")

Public API:
    result = analyze_dfa(dfa)
    result.is_valid
    result.dfa
    result.errors
"""

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional


EPSILON_SYMBOLS = {"ε", "ϵ", "epsilon", "EPSILON", "λ", "lambda", "LAMBDA"}


@dataclass
class SemanticError:
    code: str
    message: str
    line: Optional[int] = None

    def __str__(self) -> str:
        location = f" (line {self.line})" if self.line is not None else ""
        return f"[{self.code}] {self.message}{location}"


@dataclass
class SymbolTable:
    """Stores the names declared in a DFA specification."""
    states: set[str] = field(default_factory=set)
    input_symbols: set[str] = field(default_factory=set)

    def add_state(self, state: str) -> bool:
        if state in self.states:
            return False
        self.states.add(state)
        return True

    def add_input_symbol(self, symbol: str) -> bool:
        if symbol in self.input_symbols:
            return False
        self.input_symbols.add(symbol)
        return True

    def contains_state(self, state: str) -> bool:
        return state in self.states

    def contains_input_symbol(self, symbol: str) -> bool:
        return symbol in self.input_symbols


@dataclass
class SemanticResult:
    is_valid: bool
    dfa: Optional[dict[str, Any]]
    errors: list[SemanticError]
    symbol_table: SymbolTable

    def print_errors(self) -> None:
        for error in self.errors:
            print(error)


def _first_present(data: dict, *keys: str, default=None):
    for key in keys:
        if key in data:
            return data[key]
    return default


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _transition_parts(transition: Any):
    """Return (source, input_symbol, destination, line) from supported formats."""
    if isinstance(transition, dict):
        source = _first_present(transition, "from", "source", "state", "current_state")
        symbol = _first_present(transition, "symbol", "input", "input_symbol")
        destination = _first_present(
            transition, "to", "destination", "target", "next_state"
        )
        line = transition.get("line")
        return source, symbol, destination, line

    if isinstance(transition, (list, tuple)) and len(transition) >= 3:
        line = transition[3] if len(transition) >= 4 else None
        return transition[0], transition[1], transition[2], line

    return None, None, None, None


def analyze_dfa(dfa: dict[str, Any], require_complete: bool = True) -> SemanticResult:
    """
    Validate the semantic rules of a DFA.

    A valid DFA must have:
      - unique declared states and input symbols;
      - a declared start state;
      - only declared final states;
      - transitions whose source/destination states and input symbols exist;
      - no epsilon transitions;
      - at most one destination for each (state, input-symbol) pair;
      - exactly one transition for every pair when require_complete=True.

    Returns a SemanticResult. The normalized DFA is supplied only when valid.
    """
    errors: list[SemanticError] = []
    table = SymbolTable()

    if not isinstance(dfa, dict):
        errors.append(SemanticError(
            "INVALID_DFA_INPUT",
            "The parser must pass the DFA to semantic analysis as a dictionary."
        ))
        return SemanticResult(False, None, errors, table)

    states_value = _first_present(dfa, "states", "Q", "all_states", default=[])
    alphabet_value = _first_present(
        dfa, "alphabet", "input_symbols", "sigma", "Σ", default=[]
    )
    start_state = _first_present(dfa, "start_state", "start", "q0")
    final_states_value = _first_present(
        dfa, "final_states", "accepting_states", "F", default=[]
    )
    transitions_value = _first_present(dfa, "transitions", "delta", "δ", default=[])

    states = _as_list(states_value)
    alphabet = _as_list(alphabet_value)
    final_states = _as_list(final_states_value)
    transitions = _as_list(transitions_value)

    # 1. Validate declarations and build the symbol table.
    for state in states:
        if not isinstance(state, str) or not state.strip():
            errors.append(SemanticError(
                "INVALID_STATE_DECLARATION",
                f"Invalid state declaration: {state!r}."
            ))
            continue
        state = state.strip()
        if not table.add_state(state):
            errors.append(SemanticError(
                "DUPLICATE_STATE",
                f"State '{state}' has been declared more than once."
            ))

    for symbol in alphabet:
        if not isinstance(symbol, str) or not symbol.strip():
            errors.append(SemanticError(
                "INVALID_SYMBOL_DECLARATION",
                f"Invalid input-symbol declaration: {symbol!r}."
            ))
            continue
        symbol = symbol.strip()
        if symbol in EPSILON_SYMBOLS:
            errors.append(SemanticError(
                "EPSILON_IN_ALPHABET",
                "A DFA alphabet must not contain an epsilon symbol."
            ))
        if not table.add_input_symbol(symbol):
            errors.append(SemanticError(
                "DUPLICATE_INPUT_SYMBOL",
                f"Input symbol '{symbol}' has been declared more than once."
            ))

    if not table.states:
        errors.append(SemanticError(
            "EMPTY_STATE_SET",
            "The DFA must declare at least one state."
        ))

    if not table.input_symbols:
        errors.append(SemanticError(
            "EMPTY_ALPHABET",
            "The DFA must declare at least one input symbol."
        ))

    # 2. Validate the start state.
    if not isinstance(start_state, str) or not start_state.strip():
        errors.append(SemanticError(
            "MISSING_START_STATE",
            "The DFA must specify a start state."
        ))
    elif not table.contains_state(start_state.strip()):
        errors.append(SemanticError(
            "UNDEFINED_START_STATE",
            f"Start state '{start_state}' is not declared in the state set."
        ))
    else:
        start_state = start_state.strip()

    # 3. Validate final/accepting states.
    clean_final_states = []
    seen_finals = set()
    for state in final_states:
        if not isinstance(state, str) or not state.strip():
            errors.append(SemanticError(
                "INVALID_FINAL_STATE",
                f"Invalid final-state entry: {state!r}."
            ))
            continue
        state = state.strip()
        if state in seen_finals:
            errors.append(SemanticError(
                "DUPLICATE_FINAL_STATE",
                f"Final state '{state}' is listed more than once."
            ))
            continue
        seen_finals.add(state)
        clean_final_states.append(state)
        if not table.contains_state(state):
            errors.append(SemanticError(
                "UNDEFINED_FINAL_STATE",
                f"Final state '{state}' is not declared in the state set."
            ))

    # 4. Validate transitions and detect nondeterminism.
    normalized_transitions = []
    transition_destinations = {}
    seen_transition_records = set()

    for index, transition in enumerate(transitions, start=1):
        source, symbol, destination, line = _transition_parts(transition)

        if source is None or symbol is None or destination is None:
            errors.append(SemanticError(
                "MALFORMED_TRANSITION",
                f"Transition {index} must contain source, input symbol and destination."
            ))
            continue

        if not all(isinstance(value, str) and value.strip()
                   for value in (source, symbol, destination)):
            errors.append(SemanticError(
                "MALFORMED_TRANSITION",
                f"Transition {index} contains an empty or invalid value.",
                line
            ))
            continue

        source, symbol, destination = (
            source.strip(), symbol.strip(), destination.strip()
        )

        if symbol in EPSILON_SYMBOLS:
            errors.append(SemanticError(
                "EPSILON_TRANSITION",
                f"Transition from '{source}' uses epsilon; DFA transitions must consume an input symbol.",
                line
            ))
            continue

        valid_transition = True

        if not table.contains_state(source):
            errors.append(SemanticError(
                "UNDEFINED_TRANSITION_SOURCE",
                f"Transition source state '{source}' is not declared.",
                line
            ))
            valid_transition = False

        if not table.contains_input_symbol(symbol):
            errors.append(SemanticError(
                "UNDEFINED_TRANSITION_SYMBOL",
                f"Input symbol '{symbol}' is not declared in the alphabet.",
                line
            ))
            valid_transition = False

        if not table.contains_state(destination):
            errors.append(SemanticError(
                "UNDEFINED_TRANSITION_DESTINATION",
                f"Destination state '{destination}' is not declared.",
                line
            ))
            valid_transition = False

        if not valid_transition:
            continue

        key = (source, symbol)
        record = (source, symbol, destination)

        if record in seen_transition_records:
            errors.append(SemanticError(
                "DUPLICATE_TRANSITION",
                f"Transition ({source}, {symbol}) -> {destination} is repeated.",
                line
            ))
            continue

        seen_transition_records.add(record)

        if key in transition_destinations:
            previous_destination = transition_destinations[key]
            errors.append(SemanticError(
                "NONDETERMINISTIC_TRANSITION",
                f"State '{source}' has more than one destination for input "
                f"'{symbol}' ('{previous_destination}' and '{destination}').",
                line
            ))
            continue

        transition_destinations[key] = destination
        normalized_transitions.append({
            "from": source,
            "symbol": symbol,
            "to": destination,
            **({"line": line} if line is not None else {})
        })

    # 5. Check completeness: every state must define every alphabet input.
    if require_complete:
        for state in sorted(table.states):
            for symbol in sorted(table.input_symbols):
                if (state, symbol) not in transition_destinations:
                    errors.append(SemanticError(
                        "MISSING_TRANSITION",
                        f"Missing transition for state '{state}' with input '{symbol}'."
                    ))

    normalized_dfa = {
        "name": dfa.get("name", "DFA"),
        "states": sorted(table.states),
        "alphabet": sorted(table.input_symbols),
        "start_state": start_state,
        "final_states": clean_final_states,
        "transitions": normalized_transitions,
    }

    return SemanticResult(
        is_valid=(len(errors) == 0),
        dfa=normalized_dfa if not errors else None,
        errors=errors,
        symbol_table=table
    )


def print_semantic_result(result: SemanticResult) -> None:
    """Print a readable validation summary."""
    if result.is_valid:
        print("\nSemantic Analysis: PASSED")
        print("The DFA is semantically valid.")
        print("States:", ", ".join(sorted(result.symbol_table.states)))
        print("Input symbols:", ", ".join(sorted(result.symbol_table.input_symbols)))
    else:
        print("\nSemantic Analysis: FAILED")
        print(f"{len(result.errors)} semantic error(s) found:")
        for number, error in enumerate(result.errors, start=1):
            print(f"{number}. {error}")


if __name__ == "__main__":
    # Example DFA for testing this module independently.
    sample_dfa = {
        "name": "M",
        "states": ["q0", "q1"],
        "alphabet": ["0", "1"],
        "start_state": "q0",
        "final_states": ["q1"],
        "transitions": [
            ("q0", "0", "q1"),
            ("q0", "1", "q0"),
            ("q1", "0", "q1"),
            ("q1", "1", "q0"),
        ],
    }

    result = analyze_dfa(sample_dfa)
    print_semantic_result(result)
