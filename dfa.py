"""DFA execution engine: process input strings after semantic validation."""


# The executor assumes semantic analysis has already validated the DFA.
# It follows one transition per input character and records the visited states.
class DFAExecutor:
    def __init__(self, dfa_data):
        self.name = dfa_data["name"]
        self.states = set(dfa_data["states"])
        self.alphabet = set(dfa_data["alphabet"])
        self.start_state = dfa_data["start_state"]
        self.final_states = set(dfa_data["final_states"])
        self.transitions = {}

        for transition in dfa_data["transitions"]:
            if isinstance(transition, dict):
                source = transition["source"]
                symbol = transition["symbol"]
                destination = transition["destination"]
            else:
                source, symbol, destination = transition
            self.transitions[(source, symbol)] = destination

    # Return whether the string is accepted, plus a trace useful for debugging.
    def run(self, input_string):
        """Return acceptance status and the state-by-state execution trace."""
        current = self.start_state
        trace = [current]

        # Read the input from left to right, updating the current state each time.
        for position, symbol in enumerate(input_string):
            if symbol not in self.alphabet:
                return {
                    "accepted": False,
                    "reason": f"Unknown input symbol {symbol!r} at position {position}.",
                    "trace": trace,
                    "final_state": current,
                }

            next_state = self.transitions.get((current, symbol))
            if next_state is None:
                return {
                    "accepted": False,
                    "reason": f"No transition defined for ({current}, {symbol}).",
                    "trace": trace,
                    "final_state": current,
                }

            current = next_state
            trace.append(current)

        # A string is accepted exactly when processing ends in a final state.
        accepted = current in self.final_states
        return {
            "accepted": accepted,
            "reason": "Input accepted." if accepted else "Input rejected.",
            "trace": trace,
            "final_state": current,
        }
