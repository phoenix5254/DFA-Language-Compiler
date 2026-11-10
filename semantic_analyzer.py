"""Semantic checks for deterministic finite automata."""

from collections import Counter, defaultdict
from semantic_errors import SemanticDiagnostic


# Semantic analysis checks meaning after the source has passed lexical and
# syntax analysis. It resolves every state and symbol against its declaration.
class SemanticAnalyzer:
    def __init__(self, dfa):
        self.dfa = dfa
        self.errors = []
        self.state_table = {}
        self.alphabet_table = {}
        self.transition_table = defaultdict(list)

    def error(self, code, message):
        self.errors.append(SemanticDiagnostic(code, message))

    # Build the state symbol table and reject empty or duplicate state sets.
    def check_states(self):
        states = self.dfa.states
        if not states:
            self.error("SEM001", "Q must contain at least one state.")
        for state, count in Counter(states).items():
            if count > 1:
                self.error("SEM003", f"State {state!r} is declared more than once.")
        self.state_table = {state: "STATE" for state in states}

    # Build the input-symbol table; duplicate alphabet entries are invalid.
    def check_alphabet(self):
        alphabet = self.dfa.alphabet
        if not alphabet:
            self.error("SEM002", "Σ must contain at least one input symbol.")
        for symbol, count in Counter(alphabet).items():
            if count > 1:
                self.error("SEM004", f"Input symbol {symbol!r} is declared more than once.")
        self.alphabet_table = {symbol: "INPUT_SYMBOL" for symbol in alphabet}

    # The start state and all accepting states must be declared in Q.
    def check_start_and_final_states(self):
        if self.dfa.start_state not in self.state_table:
            self.error(
                "SEM005",
                f"Starting state {self.dfa.start_state!r} is not declared in Q."
            )

        for state, count in Counter(self.dfa.final_states).items():
            if state not in self.state_table:
                self.error("SEM006", f"Final state {state!r} is not declared in Q.")
            if count > 1:
                self.error("SEM006", f"Final state {state!r} appears more than once in F.")

    # Resolve transition references and ensure each pair has at most one target.
    def check_transitions(self):
        for number, (source, symbol, destination) in enumerate(
            self.dfa.transitions, start=1
        ):
            if source not in self.state_table:
                self.error("SEM007", f"Transition {number}: source state {source!r} is not in Q.")

            if symbol not in self.alphabet_table:
                self.error("SEM009", f"Transition {number}: symbol {symbol!r} is not in Σ.")

            if str(symbol).lower() in {"ε", "epsilon", "eps"}:
                self.error("SEM012", "Epsilon transitions are not allowed in a DFA.")

            if destination not in self.state_table:
                self.error(
                    "SEM008",
                    f"Transition {number}: destination state {destination!r} is not in Q."
                )

            self.transition_table[(source, symbol)].append(destination)

        for (source, symbol), destinations in self.transition_table.items():
            if len(destinations) > 1:
                self.error(
                    "SEM010",
                    f"δ({source}, {symbol}) has multiple definitions: {destinations}."
                )

    # A DFA must define a destination for every state/symbol combination.
    def check_completeness(self):
        for state in self.dfa.states:
            for symbol in self.dfa.alphabet:
                destinations = self.transition_table.get((state, symbol), [])
                if len(destinations) == 0:
                    self.error(
                        "SEM011",
                        f"Missing transition δ({state}, {symbol})."
                    )

    # Run all semantic checks and return one structured compiler result.
    def analyze(self):
        self.check_states()
        self.check_alphabet()
        self.check_start_and_final_states()
        self.check_transitions()
        self.check_completeness()

        valid = not self.errors
        return {
            "success": valid,
            "stage": "semantic",
            "message": "DFA is semantically valid." if valid else
                       f"Found {len(self.errors)} semantic error(s).",
            "errors": [error.to_dict() for error in self.errors],
            "dfa": self.dfa.to_dict() if valid else None,
        }


def analyze_dfa(dfa):
    return SemanticAnalyzer(dfa).analyze()
