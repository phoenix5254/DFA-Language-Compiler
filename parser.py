# parser.py
"""
DFA Language Project
CIT4004 - Analysis of Programming Languages
3


Stage 2 of the pipeline. Uses PLY's yacc module. Accepts tokens from the
lexer (Stage 1). Parses according to the grammar and if it matches the
input, returns a Python dictionary to be used by the semantic analyzer
(Stage 3). The semantic analyzer checks for any validity issues with the
DFA such as missing or non-deterministic transitions.

The following p_ functions define the grammar rules. A parser is generated
by PLY. Any syntax errors will be reported with PAR001+

The parser consists of:
1. The grammar rules (p_ functions). This gathers the matching input.
2. A function called build_dfa(). This function parses through the statements
in order. It ensures that nothing is used before it is defined. Transition
tables are split into transitions. The DFA dictionary is built.

The table rule is simply δ name as the lexer doesn't return NEWLINE tokens.
The names are split into a header (one name for each symbol in Σ) and rows
(label with one name for each symbol in Σ) in build_dfa().

Q, Σ, δ, q0 and F are all given the KEYWORDS token by the lexer. They are
converted to unique tokens (KW_Q, KW_SIGMA, KW_DELTA, KW_Q0, KW_F). q0 is
considered a keyword if it is followed by '=' otherwise it is a name. X
between Q and Σ is converted to CROSS. Otherwise it is a name.

Public API
dfa, errors = parse(tokens)

tokens: Tokens from the lexer. Each has .type, .value (and optionally .lineno/.line).
DFA: Dictionary to be used by analyze_dfa() in semantic_analyzer.py. None if there was an error.
errors: List of ParserError objects. Empty if no errors.

If this file is run, a small console demo will be run (run()).
"""

import ply.yacc as yacc
from dataclasses import dataclass
from typing import Optional

# ============================================================
# Constants
# ============================================================

# PLY requires this list, and it must name every token the grammar uses.
tokens = [
    "IDENTIFIER",
    "NUMBER",
    "EQUAL",
    "COMMA",
    "LBRACE",
    "RBRACE",
    "LPAREN",
    "RPAREN",
    "ARROW",
    "CROSS",
    "KW_Q",
    "KW_SIGMA",
    "KW_DELTA",
    "KW_Q0",
    "KW_F",
]

# Where the grammar starts.
start = "program"

# Text of each keyword -> its own token type.
KEYWORD_TYPES = {
    "Q": "KW_Q",
    "Σ": "KW_SIGMA",
    "δ": "KW_DELTA",
    "F": "KW_F",
}

# The five components, in the order the project brief gives them.
NAMED_TUPLE_ORDER = ["Q", "Σ", "δ", "q0", "F"]

# myTokenizer.py stores no text (value is None) for punctuation; this table
# supplies the text so error messages have something to show.
PUNCTUATION_TEXT = {
    "EQUAL": "=",
    "COMMA": ",",
    "LBRACE": "{",
    "RBRACE": "}",
    "LPAREN": "(",
    "RPAREN": ")",
    "ARROW": "->",
    "CROSS": "X",
}

END_OF_PROGRAM = "<end of program>"

# ============================================================
# Error Model
# ============================================================

# myTokenizer.py has no text for punctuation (None). This table
# provides a consistent way for all syntax errors to be reported. So
# the rest of the project can handle parser output consistently. Once
# returned, it can't be accidentally modified (frozen=True).
@dataclass(frozen=True)
class ParserError:
    code: str
    message: str

    # Line of the offending token. None when the lexer gives no line numbers.
    line: Optional[int]

    # Position of the offending token in the token list (0 = first token).
    token_index: int
    token_text: str

    stage: str = "SYNTAX"

    def __str__(self) -> str:
        if self.line is not None:
            where = f"line {self.line}"
        else:
            where = f"token #{self.token_index + 1}"
        if self.token_text == END_OF_PROGRAM:
            where = where + ", at end of program" if self.line is not None else "at end of program"
        return f"[{self.code}] {self.message} ({where})"


# Raised by any error in the PLY machinery (p_error or action). The
# parse() method will catch this and turn it into a ParserError.
# token=None indicates that the error was at the end of the program.
class ParseFailure(Exception):

    def __init__(self, code, message, token=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.token = token


def make_error(code, message, token):
    # Build a ParserError that points at one token.
    return ParserError(
        code=code,
        message=message,
        line=token.lineno,
        token_index=token.index,
        token_text=str(token.value)
    )


def failure_to_error(failure, token_list):
    #Turn a ParseFailure into a ParserError (placing end-of-program errors)
    if failure.token is not None:
        return make_error(failure.code, failure.message, failure.token)

    last_line = None
    if len(token_list) > 0:
        last_line = token_list[len(token_list) - 1].lineno

    return ParserError(
        failure.code, failure.message, last_line, len(token_list), END_OF_PROGRAM
    )


# ============================================================
# Token Preparation
# ============================================================

# The parser in PLY uses an object which has a token() method to get tokens. The
# token passed to it is the token from the lexer. It has been adjusted to fit
# the format expected by the grammar. PLY looks for the type and value
# attributes (and lineno/lexpos for internal use). The index is our own and
# used only for error reporting.
class FeedToken:

    def __init__(self, token_type, value, lineno, index):
        self.type = token_type
        self.value = value
        self.lineno = lineno
        self.lexpos = index
        self.index = index


# Hands the prepared tokens to PLY one at a time. Returning None tells PLY the
# input has ended.
class TokenFeed:

    def __init__(self, token_list):
        self.token_list = token_list
        self.position = 0

    def input(self, data):
        # PLY may call this; the tokens were supplied in the constructor.
        pass

    def token(self):
        if self.position < len(self.token_list):
            tok = self.token_list[self.position]
            self.position += 1
            return tok
        return None


def prepare_tokens(raw_tokens):
    
    # Convert the tokens from the lexer into FeedTokens (see the comments at the top
    # of the file for why keywords are split into separate types).

    # "RESERVED WORD" and "RESERVED_WORD" are treated the same. The NEWLINE
    # tokens are removed. The NUMBER is converted into a string. The lexer converts
    # "0" into 0 (an integer) and "01" into 1. So leading zeros will be lost.
    

    # Step 1: simplify every token to (type, text, line).
    cleaned = []

    for raw in raw_tokens:

        token_type = str(raw.type).replace(" ", "_")

        if token_type == "NEWLINE":
            continue

        if raw.value is None:
            text = PUNCTUATION_TEXT.get(token_type, token_type)
        else:
            text = str(raw.value)

        # Use line number from lexer (called 'lineno' or 'line'). myTokenizer.py
        # does not provide line numbers, so line will be None. Errors will be
        # reported by token number. getattr with default means use None if
        # attribute does not exist.
        line = getattr(raw, "lineno", None)
        if line is None:
            line = getattr(raw, "line", None)

        cleaned.append((token_type, text, line))

    # Step 2: give keywords their own types. This needs to peek at the
    # neighbouring tokens, which is why it is a second pass.
    result = []

    for i in range(len(cleaned)):

        token_type, text, line = cleaned[i]

        previous_text = None
        if i > 0:
            previous_text = cleaned[i - 1][1]

        next_type = None
        next_text = None
        if i + 1 < len(cleaned):
            next_type = cleaned[i + 1][0]
            next_text = cleaned[i + 1][1]

        if token_type == "KEYWORDS":
            if text == "q0":
                # keyword in "q0 = ...", an ordinary state name otherwise
                if next_type == "EQUAL":
                    token_type = "KW_Q0"
                else:
                    token_type = "IDENTIFIER"
            else:
                token_type = KEYWORD_TYPES.get(text, "KEYWORDS")

        elif token_type == "IDENTIFIER" and text == "X":
            # only the X in "... Q X Σ ..." is the cross sign
            if previous_text == "Q" and next_text == "Σ":
                token_type = "CROSS"

        result.append(FeedToken(token_type, text, line, len(result)))

    return result


# ============================================================
# Bracket Check
# ============================================================

# Correct bracketing.
# A stack is used to ensure all brackets are properly balanced. Brackets
# are pushed onto the stack if they are opening brackets. Closing
# brackets must match the top of the stack. This is performed before
# parsing so that all errors relating to brackets can be given at once,
# with more descriptive error messages.
def check_brackets(token_list):
    #Return a list of ParserError for every bracket mistake (empty = fine).
    errors = []
    open_brackets = []

    for tok in token_list:

        if tok.type == "LPAREN" or tok.type == "LBRACE":
            open_brackets.append(tok)

        elif tok.type == "RPAREN" or tok.type == "RBRACE":

            if len(open_brackets) == 0:
                errors.append(make_error(
                    "PAR003",
                    f"Closing '{tok.value}' has no matching opening bracket",
                    tok
                ))
            else:
                opener = open_brackets.pop()
                paired = (
                    (opener.type == "LPAREN" and tok.type == "RPAREN")
                    or (opener.type == "LBRACE" and tok.type == "RBRACE")
                )
                if not paired:
                    errors.append(make_error(
                        "PAR004",
                        f"Mismatched brackets: '{opener.value}' was closed by '{tok.value}'",
                        tok
                    ))

    for opener in open_brackets:
        errors.append(make_error(
            "PAR005",
            f"Opening '{opener.value}' is never closed",
            opener
        ))

    return errors


# ============================================================
# PART 1 - THE GRAMMAR
#
# PLY parses all functions starting with p_. Each function's docstring
# represents a rule. Rules:
#  - THE rule is in THE form: "left side : right side"
#  - p[1], p[2] ... are THE values of THE right hand side. p[0] will
#   be THE value of this rule.
#  - p.slice[n] is THE actual token object. It is used to store THE line
#   number of THE token.
#  - Comments are given ABOVE each function to explain what it does. The
#   docstring is reserved for THE rule.
# ============================================================

# ---------------- program ----------------
# Two different types of tuples, which means two different types of

# bodies. Definitions (Q = ..., δ = ...) can only come after THE named
# tuple as there is nothing to define in THE inline tuple. This is
# enforced by having two separate rules. All of THE real work is done in
# build_dfa().
def p_program_named(p):
    'program : IDENTIFIER EQUAL named_tuple named_body'
    p[0] = build_dfa(p.slice[1], True, None, p[4])


def p_program_inline(p):
    'program : IDENTIFIER EQUAL inline_tuple inline_body'
    p[0] = build_dfa(p.slice[1], False, p[3], p[4])


# ---------------- the two tuples ----------------

# Format A: just the component names. Their values are given below.
# The lexer has generated q0 as a normal name with no '=' following it, so
# the fourth component is tested for its text.
def p_named_tuple(p):
    'named_tuple : LPAREN KW_Q COMMA KW_SIGMA COMMA KW_DELTA COMMA IDENTIFIER COMMA KW_F RPAREN'
    if p[8] != "q0":
        raise ParseFailure(
            "PAR001",
            f"Expected 'q0' as component 4 of the 5-tuple but found '{p[8]}'",
            p.slice[8]
        )
    p[0] = None


# Format B: every component written out. The values are kept as token
# objects so later checks can point at them.
def p_inline_tuple(p):
    'inline_tuple : LPAREN name_set COMMA name_set COMMA KW_DELTA COMMA name COMMA name_set RPAREN'
    p[0] = {
        "states": p[2],
        "alphabet": p[4],
        "start": p[8],
        "finals": p[10],
    }


# ---------------- bodies (lists of statements, in the order written) ----------------

def p_named_body_more(p):
    'named_body : named_body named_statement'
    p[0] = p[1] + [p[2]]


def p_named_body_empty(p):
    'named_body : empty'
    p[0] = []


def p_inline_body_more(p):
    'inline_body : inline_body inline_statement'
    p[0] = p[1] + [p[2]]


def p_inline_body_empty(p):
    'inline_body : empty'
    p[0] = []


def p_named_statement(p):
    '''named_statement : definition
                       | delta_decl
                       | transition
                       | table'''
    p[0] = p[1]


def p_inline_statement(p):
    '''inline_statement : transition
                        | table'''
    p[0] = p[1]


# ---------------- statements ----------------
# Each statement becomes a tuple whose first item says what it is. Tokens are
# kept (not just their text) so errors found later can name a line.

# Q = {...}   Σ = {...}   F = {...}
def p_definition_set(p):
    '''definition : KW_Q EQUAL name_set
                  | KW_SIGMA EQUAL name_set
                  | KW_F EQUAL name_set'''
    p[0] = ("define", p.slice[1], p[3])


# q0 = q1   or, as in grammar.txt,   q0 = {q1}
def p_definition_start(p):
    '''definition : KW_Q0 EQUAL name
                  | KW_Q0 EQUAL name_set'''
    p[0] = ("define", p.slice[1], p[3])


# δ = Q X Σ -> Q
def p_delta_decl(p):
    'delta_decl : KW_DELTA EQUAL KW_Q CROSS KW_SIGMA ARROW KW_Q'
    p[0] = ("delta", p.slice[1], p.slice[3], p.slice[5])


# δ(q1,a)=q2   (a comma after it is optional, as in grammar.txt)
def p_transition(p):
    'transition : KW_DELTA LPAREN name COMMA name RPAREN EQUAL name optional_comma'
    p[0] = ("transition", p.slice[1], p[3], p[5], p[8])


# δ a b c  q1 q2 q3 ...   -- a flat run of names; cut into rows in build_dfa
def p_table(p):
    'table : KW_DELTA name_run'
    p[0] = ("table", p.slice[1], p[2])


def p_optional_comma(p):
    '''optional_comma : COMMA
                      | empty'''
    p[0] = None


# ---------------- sets and names ----------------

# { }  is grammatical; the semantic analyzer rejects an empty set of states.
def p_name_set_empty(p):
    'name_set : LBRACE RBRACE'
    p[0] = []


def p_name_set_filled(p):
    'name_set : LBRACE name_list RBRACE'
    p[0] = p[2]


def p_name_list_one(p):
    'name_list : name'
    p[0] = [p[1]]


def p_name_list_more(p):
    'name_list : name_list COMMA name'
    p[0] = p[1] + [p[3]]


def p_name_run_one(p):
    'name_run : name'
    p[0] = [p[1]]


def p_name_run_more(p):
    'name_run : name_run name'
    p[0] = p[1] + [p[2]]


# A name is a state or a symbol. The value kept is the token itself.
def p_name(p):
    '''name : IDENTIFIER
            | NUMBER'''
    p[0] = p.slice[1]


# A rule that matches nothing. Used where something may be absent.
def p_empty(p):
    'empty :'
    pass


# Called by PLY at the first token that fits no rule (token is None when the
# program ends too early). Raising stops the parse at the first syntax error:
# after one, any further "errors" would only be guesses.
def p_error(token):
    if token is None:
        raise ParseFailure(
            "PAR002",
            "Unexpected end of program (something is unfinished)",
            None
        )

    if token.type.startswith("KW_") or token.type == "RESERVED_WORD":
        raise ParseFailure(
            "PAR007",
            f"Unexpected reserved word '{token.value}' (reserved words cannot be state "
            f"or symbol names, and 'Q = ...' style definitions need the format "
            f"(Q, Σ, δ, q0, F))",
            token
        )

    raise ParseFailure("PAR001", f"Unexpected '{token.value}'", token)


# ============================================================
# PART 2 - BUILDING THE DFA
#
# The grammar has accepted the program. Now the statements are processed in
# the order they were written. Order matters: a symbol cannot be used before
# it is defined (project brief). That is a property of the text, and the
# semantic analyzer only sees the finished dictionary, so it is checked here.
# ============================================================

def fail(code, message, token):
    raise ParseFailure(code, message, token)


def values_of(name_tokens):
    # The text of each name token, in order (duplicates are kept).
    result = []
    for tok in name_tokens:
        result.append(tok.value)
    return result


def require_delta_ready(named, defined, delta_token):
    
    # In the named format transitions can only appear after δ = Q X Σ -> Q
    # (which requires Q and Σ). In the inline format δ is part of the tuple so
    # there is nothing to check.
    
    if named and "δ" not in defined:
        fail(
            "PAR006",
            "Transitions are used before 'δ = Q X Σ -> Q' has been written",
            delta_token
        )


def same_line(first_token, other_token):
    # False only when both lines are known and they differ.
    if first_token.lineno is None or other_token.lineno is None:
        return True
    return first_token.lineno == other_token.lineno


def add_table(dfa, delta_token, names):
    
    #Split the flat list of names after δ into a header and rows. Convert the
    #rows into normal transitions. A table is just a shorthand notation for
    #many δ(q,a)=r statements.

    #Header : One name per symbol in Σ.
    #R  ow  : State name followed by one destination per symbol in Σ.

    #If your lexer provides line numbers then the header and row should be
    #single lines. This way you get a clear error message if the row is too short.

    column_count = len(dfa["alphabet"])

    if column_count == 0:
        fail("PAR014", "Cannot read the transition table: the alphabet is empty", delta_token)

    if len(names) < column_count:
        fail(
            "PAR010",
            f"The table header has only {len(names)} entries but {column_count} are needed "
            f"(one per input symbol)",
            delta_token
        )

    header = names[0:column_count]

    for tok in header:
        if not same_line(delta_token, tok):
            fail(
                "PAR010",
                f"The table header has fewer than {column_count} entries on its line "
                f"(one per input symbol is needed)",
                delta_token
            )

    position = column_count

    while position < len(names):

        label = names[position]
        entries = names[position + 1: position + 1 + column_count]

        too_short = len(entries) < column_count
        for tok in entries:
            if not same_line(label, tok):
                too_short = True

        if too_short:
            fail(
                "PAR010",
                f"The row for '{label.value}' has too few entries "
                f"({column_count} are needed, one per input symbol)",
                label
            )

        for i in range(column_count):
            dfa["transitions"].append({
                "from": label.value,
                "symbol": header[i].value,
                "to": entries[i].value,
                "line": label.lineno,
            })

        position += column_count + 1


def build_dfa(name_token, named, tuple_data, statements):
    
    #Dictionary to be used for the semantic analyzer.

    #named = True if it is a format A, False otherwise
    #tuple_data = values inside the tuple (only format B)
    #statements = statements found after the tuple (in order)
    
    dfa = {
        "name": name_token.value,
        "states": [],
        "alphabet": [],
        "start_state": None,
        "final_states": [],
        "transitions": [],
    }

    # Components already defined (format A): "Q", "Σ", "δ", "q0", "F".
    # This is what makes "used before defined" checkable.
    defined = set()

    if not named:
        dfa["states"] = values_of(tuple_data["states"])
        dfa["alphabet"] = values_of(tuple_data["alphabet"])
        dfa["start_state"] = tuple_data["start"].value
        dfa["final_states"] = values_of(tuple_data["finals"])

    for statement in statements:

        kind = statement[0]

        # ---- Q = {...}   Σ = {...}   F = {...}   q0 = ... ----
        if kind == "define":
            keyword_token = statement[1]
            value = statement[2]
            component = keyword_token.value

            if component in defined:
                fail("PAR008", f"'{component}' is defined more than once", keyword_token)

            if component == "Q":
                dfa["states"] = values_of(value)

            elif component == "Σ":
                dfa["alphabet"] = values_of(value)

            elif component == "F":
                dfa["final_states"] = values_of(value)

            else:
                # q0: a set (must hold exactly one state) or a single name
                if isinstance(value, list):
                    if len(value) != 1:
                        fail(
                            "PAR011",
                            f"The start state must be exactly one state, but {len(value)} were given",
                            keyword_token
                        )
                    dfa["start_state"] = value[0].value
                else:
                    dfa["start_state"] = value.value

            defined.add(component)

        # ---- δ = Q X Σ -> Q ----
        elif kind == "delta":
            delta_token = statement[1]
            q_token = statement[2]
            sigma_token = statement[3]

            if "δ" in defined:
                fail("PAR008", "'δ' is defined more than once", delta_token)

            # The brief's own example: δ = Q × Σ → Q cannot appear before Q
            # and Σ have been defined.
            if "Q" not in defined:
                fail(
                    "PAR006",
                    "'Q' is used in the definition of δ before 'Q = {...}' has been written",
                    q_token
                )

            if "Σ" not in defined:
                fail(
                    "PAR006",
                    "'Σ' is used in the definition of δ before 'Σ = {...}' has been written",
                    sigma_token
                )

            defined.add("δ")

        # ---- δ(q1,a)=q2 ----
        elif kind == "transition":
            delta_token = statement[1]
            require_delta_ready(named, defined, delta_token)

            dfa["transitions"].append({
                "from": statement[2].value,
                "symbol": statement[3].value,
                "to": statement[4].value,
                "line": delta_token.lineno,
            })

        # ---- δ a b c ... (table) ----
        else:
            delta_token = statement[1]
            require_delta_ready(named, defined, delta_token)
            add_table(dfa, delta_token, statement[2])

    # Nothing the tuple promised may be missing.
    if named:
        for component in NAMED_TUPLE_ORDER:
            if component not in defined:
                fail(
                    "PAR009",
                    f"'{component}' is listed in the 5-tuple but never defined",
                    None
                )

    return dfa


# ============================================================
# Public API
# ============================================================

def parse(raw_tokens):
    
    # Ensure that the tokens are grammatically correct.

    # Returns a tuple with (dfa, errors)
    # If successful, returns (dictionary for semantic analyzer, empty list)
    # If unsuccessful, returns (None, [ParserError, ...])

    # Do not perform semantic analysis if there are any errors.
    
    token_list = prepare_tokens(raw_tokens)

    # Bracket mistakes first: all are reported at once and the real parse is
    # skipped, because it would only repeat them confusingly.
    bracket_errors = check_brackets(token_list)
    if len(bracket_errors) > 0:
        return None, bracket_errors

    # PLY builds the parser from the p_ functions above. write_tables=False
    # keeps it from creating parsetab.py / parser.out files in the project.
    plyparser = yacc.yacc(debug=False, write_tables=False)

    try:
        dfa = plyparser.parse(lexer=TokenFeed(token_list))
    except ParseFailure as failure:
        return None, [failure_to_error(failure, token_list)]

    return dfa, []


# ============================================================
# Console Demo (run this file to try it)
# ============================================================

# Each sample is a full program. They are stored here so the symbols Σ and δ
# do not have to be typed in the terminal.
SAMPLE_PROGRAMS = {
    "Format A with a transition table (from the brief)": """\
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
""",

    "Format B, one line of transitions (from the brief)": """\
M = ({q1, q2, q3, q4, Trap}, {a, b, c}, δ, q1, {q4})
δ(q1,a)=q2 δ(q1,b)=q3 δ(q1,c)=Trap δ(q2,a)=q4 δ(q2,b)=Trap δ(q2,c)=q2
δ(q3,a)=Trap δ(q3,b)=q4 δ(q3,c)=q3 δ(q4,a)=Trap δ(q4,b)=Trap δ(q4,c)=Trap
δ(Trap,a)=Trap δ(Trap,b)=Trap δ(Trap,c)=Trap
""",

    "Error: δ used before Σ is defined": """\
M = (Q, Σ, δ, q0, F)
Q = {q1, q2}
δ = Q X Σ -> Q
Σ = {a, b}
""",

    "Error: bracket never closed": """\
M = ({q1, q2, {a, b}, δ, q1, {q2})
""",

    "Error: transition table row too short": """\
M = ({q1, q2}, {a, b}, δ, q1, {q2})
δ a b
q1 q2
q2 q2 q2
""",
}


def get_tokens(text):
    
    #Run the lexer (myTokenizer.py). Returns (tokens, lexical_error_messages).

    #The import happens inside the function so that this file still loads
    #when myTokenizer.py is missing.
    
    from myTokenizer import Lexer

    found, error = Lexer(text).tokenizer()
    if error is not None:
        return [], [str(error)]
    return found, []


def print_dfa(dfa):
    # Show the dictionary that is handed to the semantic analyzer.
    print("  name        :", dfa["name"])
    print("  states      :", dfa["states"])
    print("  alphabet    :", dfa["alphabet"])
    print("  start state :", dfa["start_state"])
    print("  final states:", dfa["final_states"])
    print("  transitions :", len(dfa["transitions"]))
    for t in dfa["transitions"]:
        print(f"      {t['from']} --{t['symbol']}--> {t['to']}")


def process(text):
    # Lex, parse and (if possible) semantically check one program.
    print("\n--- Program ---")
    print(text)

    found, lexical_errors = get_tokens(text)
    if len(lexical_errors) > 0:
        print("--- Lexical errors ---")
        for message in lexical_errors:
            print("  ", message)
        return

    dfa, errors = parse(found)
    if len(errors) > 0:
        print(f"--- {len(errors)} syntax error(s) ---")
        for error in errors:
            print("  ", error)
        return

    print("--- Parsing succeeded. Dictionary for the semantic analyzer: ---")
    print_dfa(dfa)

    # Stage 3 is in semantic_analyzer.py; use it if it is next to this file.
    try:
        from semantic_analyzer import analyze_dfa, print_semantic_result
    except ImportError:
        print("\n(semantic_analyzer.py not found next to this file; skipping stage 3)")
        return

    print_semantic_result(analyze_dfa(dfa))


def run():
    while True:
        choice = input(
            "\nChoose an option:\n"
            "1. Run a built-in sample program\n"
            "2. Type your own program\n"
            "3. Exit\n"
            "Enter choice (1, 2, or 3): "
        )

        try:
            choice = int(choice)
        except ValueError:
            print("Invalid input. Please enter a number (1, 2, or 3).")
            continue

        if choice == 1:
            names = list(SAMPLE_PROGRAMS.keys())
            for i in range(len(names)):
                print(f"  {i + 1}. {names[i]}")

            pick = input("Which sample? ")
            try:
                pick = int(pick)
            except ValueError:
                print("Invalid input.")
                continue

            if pick < 1 or pick > len(names):
                print("No such sample.")
                continue

            process(SAMPLE_PROGRAMS[names[pick - 1]])

        elif choice == 2:
            print("Type the program. Finish with a line containing only 'exit'.")
            lines = []
            try:
                while True:
                    line = input()
                    if line.strip().lower() == 'exit':
                        break
                    lines.append(line)
            except (KeyboardInterrupt, EOFError):
                break
            process('\n'.join(lines))

        elif choice == 3:
            print("Exiting.")
            break


if __name__ == "__main__":
    run()