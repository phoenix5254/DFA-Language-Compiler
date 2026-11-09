# test_parser.py

# Test script for parser.py.
# Can run with pytest since all tests are functions beginning with test_.

# Each test will lex a small program with the hand written lexer (myTokenizer.py),
# parse it and if appropriate pass to semantic_analyzer.py to show that the
# three components work together.


from myTokenizer import Lexer
from parser import parse
from semantic_analyzer import analyze_dfa


def lex(text):
    # Lex with myTokenizer. Fails the test if the lexer itself complains.
    found, error = Lexer(text).tokenizer()
    assert error is None, f"unexpected lexical error: {error}"
    return found


def lex_with_lines(text):
    
    # myTokenizer does not give tokens line numbers. The parser uses them when
    # they exist (to say WHICH table row is too short), so to test that part,
    # lex each line separately and add a .lineno to its tokens.
    
    found = []
    line_number = 1
    for line in text.split("\n"):
        for tok in lex(line):
            tok.lineno = line_number
            found.append(tok)
        line_number += 1
    return found


def codes(errors):
    return [e.code for e in errors]


# ------------------------------------------------------------
# Programs that must be accepted
# ------------------------------------------------------------

SPEC_TABLE = """
M = (Q, Σ, δ, q0, F)
Q = {q1, q2, q3, q4, Trap}
Σ = {a, b, c}
δ = Q X Σ -> Q
q0 = q1
F = {q4}
δ a b c
q1 q2 q3 Trap
q2 q4 Trap q2
q3 Trap q4 q3
q4 Trap Trap Trap
Trap Trap Trap Trap
"""

SPEC_INLINE = """
M = ({q1, q2, q3, q4, Trap}, {a, b, c}, δ, q1, {q4})
δ(q1,a)=q2 δ(q1,b)=q3 δ(q1,c)=Trap δ(q2,a)=q4 δ(q2,b)=Trap δ(q2,c)=q2
δ(q3,a)=Trap δ(q3,b)=q4 δ(q3,c)=q3 δ(q4,a)=Trap δ(q4,b)=Trap δ(q4,c)=Trap
δ(Trap,a)=Trap δ(Trap,b)=Trap δ(Trap,c)=Trap
"""


def test_format_a_with_table_matches_semantic_analyzer():
    dfa, errors = parse(lex(SPEC_TABLE))
    assert errors == []
    assert dfa["name"] == "M"
    assert dfa["states"] == ["q1", "q2", "q3", "q4", "Trap"]
    assert dfa["alphabet"] == ["a", "b", "c"]
    assert dfa["start_state"] == "q1"
    assert dfa["final_states"] == ["q4"]
    assert len(dfa["transitions"]) == 15
    assert analyze_dfa(dfa).is_valid


def test_format_b_inline_matches_semantic_analyzer():
    dfa, errors = parse(lex(SPEC_INLINE))
    assert errors == []
    assert len(dfa["transitions"]) == 15
    assert analyze_dfa(dfa).is_valid


def test_both_formats_describe_the_same_dfa():
    a, _ = parse(lex(SPEC_TABLE))
    b, _ = parse(lex(SPEC_INLINE))
    as_tuples = lambda dfa: sorted((t["from"], t["symbol"], t["to"]) for t in dfa["transitions"])
    assert as_tuples(a) == as_tuples(b)


def test_format_a_with_transition_list_instead_of_table():
    text = """
    M = (Q, Σ, δ, q0, F)
    Q = {s, t}
    Σ = {0, 1}
    δ = Q * Σ -> Q
    q0 = s
    F = {t}
    δ(s,0)=t, δ(s,1)=s, δ(t,0)=t, δ(t,1)=s
    """
    dfa, errors = parse(lex(text))
    assert errors == []
    assert dfa["alphabet"] == ["0", "1"]          # NUMBER tokens become text
    assert analyze_dfa(dfa).is_valid


def test_format_b_with_a_table():
    text = """
    M = ({s, t}, {a, b}, δ, s, {t})
    δ a b
    s t s
    t t s
    """
    dfa, errors = parse(lex(text))
    assert errors == []
    assert analyze_dfa(dfa).is_valid


def test_q0_can_be_a_state_name_and_the_keyword_in_the_same_program():
    text = """
    M = (Q, Σ, δ, q0, F)
    Q = {q0, q1}
    Σ = {a}
    δ = Q X Σ -> Q
    q0 = {q0}
    F = {q1}
    δ a
    q0 q1
    q1 q1
    """
    dfa, errors = parse(lex(text))
    assert errors == []
    assert dfa["states"] == ["q0", "q1"]
    assert dfa["start_state"] == "q0"
    assert analyze_dfa(dfa).is_valid


def test_definitions_may_follow_the_table():
    text = """
    M = (Q, Σ, δ, q0, F)
    Q = {s}
    Σ = {a}
    δ = Q X Σ -> Q
    δ a
    s s
    q0 = s
    F = {s}
    """
    dfa, errors = parse(lex(text))
    assert errors == []
    assert dfa["start_state"] == "s"


def test_cross_sign_written_as_identifier_X_is_still_accepted():
    tokens = lex("M = (Q, Σ, δ, q0, F) Q = {s} Σ = {a} δ = Q X Σ -> Q q0 = s F = {s} δ(s,a)=s")
    for tok in tokens:
        if tok.type == "CROSS":
            tok.type = "IDENTIFIER"      # as if a lexer read X as a plain identifier
    dfa, errors = parse(tokens)
    assert errors == []


# ------------------------------------------------------------
# Programs that must be rejected by the PARSER
# ------------------------------------------------------------

def test_delta_before_sigma_is_use_before_define():
    text = "M = (Q, Σ, δ, q0, F)  Q = {s}  δ = Q X Σ -> Q  Σ = {a}"
    dfa, errors = parse(lex(text))
    assert dfa is None
    assert codes(errors) == ["PAR006"]
    assert "Σ" in errors[0].message


def test_delta_before_q_is_use_before_define():
    dfa, errors = parse(lex("M = (Q, Σ, δ, q0, F)  δ = Q X Σ -> Q"))
    assert codes(errors) == ["PAR006"]


def test_transitions_before_delta_declaration():
    text = "M = (Q, Σ, δ, q0, F) Q = {s} Σ = {a} δ(s,a)=s"
    dfa, errors = parse(lex(text))
    assert codes(errors) == ["PAR006"]


def test_missing_component_is_reported_at_the_end():
    text = "M = (Q, Σ, δ, q0, F) Q = {s} Σ = {a} δ = Q X Σ -> Q q0 = s δ(s,a)=s"
    dfa, errors = parse(lex(text))
    assert codes(errors) == ["PAR009"]
    assert "'F'" in errors[0].message


def test_duplicate_definition():
    text = "M = (Q, Σ, δ, q0, F) Q = {s} Q = {t}"
    dfa, errors = parse(lex(text))
    assert codes(errors) == ["PAR008"]


def test_definitions_not_allowed_in_inline_format():
    text = "M = ({s}, {a}, δ, s, {s}) Q = {s}"
    dfa, errors = parse(lex(text))
    assert codes(errors) == ["PAR007"]      # the grammar rejects 'Q' here


def test_start_state_set_must_have_one_element():
    text = "M = (Q, Σ, δ, q0, F) Q = {s, t} q0 = {s, t}"
    dfa, errors = parse(lex(text))
    assert codes(errors) == ["PAR011"]


def test_keyword_cannot_be_a_state_name():
    dfa, errors = parse(lex("M = ({Q, t}, {a}, δ, t, {t})"))
    assert codes(errors) == ["PAR007"]


def test_missing_equals_after_name():
    dfa, errors = parse(lex("M ({s}, {a}, δ, s, {s})"))
    assert codes(errors) == ["PAR001"]


def test_program_that_stops_early():
    dfa, errors = parse(lex("M = ({s}, {a}, δ, s,"))
    assert dfa is None
    assert "PAR005" in codes(errors)     # the '(' and '{' were never closed


def test_trailing_comma_in_a_set():
    dfa, errors = parse(lex("M = ({s,}, {a}, δ, s, {s})"))
    assert codes(errors) == ["PAR001"]


def test_empty_input():
    dfa, errors = parse([])
    assert codes(errors) == ["PAR002"]


# ------------------------------------------------------------
# Brackets
# ------------------------------------------------------------

def test_unclosed_brace():
    dfa, errors = parse(lex("M = ({s, {a}, δ, s, {s})"))
    assert dfa is None
    assert "PAR005" in codes(errors) or "PAR004" in codes(errors)


def test_mismatched_brackets():
    dfa, errors = parse(lex("M = ({s), {a}, δ, s, {s})"))
    assert "PAR004" in codes(errors)


def test_extra_closing_bracket():
    dfa, errors = parse(lex("M = ({s}, {a}, δ, s, {s}))"))
    assert codes(errors) == ["PAR003"]


# ------------------------------------------------------------
# Line-aware checks (used when the lexer provides line numbers)
# ------------------------------------------------------------

def test_row_too_short_is_reported_with_its_line_number():
    text = "M = ({q1, q2}, {a, b}, δ, q1, {q2})\nδ a b\nq1 q2\nq2 q2 q2"
    dfa, errors = parse(lex_with_lines(text))
    assert codes(errors) == ["PAR010"]
    assert errors[0].line == 3
    assert "q1" in errors[0].message


def test_header_too_short_is_reported():
    text = "M = ({q1, q2}, {a, b}, δ, q1, {q2})\nδ a\nq1 q2 q2\nq2 q2 q2"
    dfa, errors = parse(lex_with_lines(text))
    assert codes(errors) == ["PAR010"]
    assert errors[0].line == 2


def test_valid_table_with_lines_is_accepted_and_keeps_line_numbers():
    dfa, errors = parse(lex_with_lines(SPEC_TABLE))
    assert errors == []
    lines = sorted({t["line"] for t in dfa["transitions"]})
    assert lines == [9, 10, 11, 12, 13]


def test_single_line_program_is_not_wrongly_rejected():
    text = "M = ({s, t}, {a, b}, δ, s, {t}) δ a b s t s t t s"
    dfa, errors = parse(lex_with_lines(text))
    assert errors == []
    assert len(dfa["transitions"]) == 4


# ------------------------------------------------------------
# The parser leaves DFA correctness to the semantic analyzer
# ------------------------------------------------------------

def test_nondeterminism_passes_the_parser_and_fails_semantics():
    text = "M = ({s, t}, {a}, δ, s, {t}) δ(s,a)=s δ(s,a)=t δ(t,a)=t"
    dfa, errors = parse(lex(text))
    assert errors == []
    result = analyze_dfa(dfa)
    assert not result.is_valid
    assert "NONDETERMINISTIC_TRANSITION" in [e.code for e in result.errors]


def test_epsilon_word_passes_the_parser_and_fails_semantics():
    text = "M = ({s}, {a}, δ, s, {s}) δ(s,a)=s δ(s,epsilon)=s"
    dfa, errors = parse(lex(text))
    assert errors == []
    assert "EPSILON_TRANSITION" in [e.code for e in analyze_dfa(dfa).errors]


def test_missing_transitions_pass_the_parser_and_fail_semantics():
    text = "M = ({s, t}, {a, b}, δ, s, {t}) δ(s,a)=t"
    dfa, errors = parse(lex(text))
    assert errors == []
    assert "MISSING_TRANSITION" in [e.code for e in analyze_dfa(dfa).errors]


# ------------------------------------------------------------
# Runner (so `python test_parser.py` works without pytest)
# ------------------------------------------------------------

if __name__ == "__main__":
    passed = 0
    failed = 0

    for name in sorted(list(globals().keys())):
        if name.startswith("test_") and callable(globals()[name]):
            try:
                globals()[name]()
                print(f"PASS  {name}")
                passed += 1
            except AssertionError as problem:
                print(f"FAIL  {name}: {problem}")
                failed += 1
            except Exception as problem:
                print(f"ERROR {name}: {type(problem).__name__}: {problem}")
                failed += 1

    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)