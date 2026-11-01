import ply.lex as lex

# =====================================================================
# 1. KEYWORDS, RESERVED WORDS & LEXER TOKENS
# =====================================================================
RESERVE_WORDS = {'WHILE', 'IF', 'ELSE', 'FOR', 'RETURN', 'FUNCTION', 'VAR', 'LET', 'CONST'}
KEYWORDS = {'Q', 'Σ', 'F', 'δ', 'q0'}

# Master list of token names required by PLY
tokens = (
    'IDENTIFIER',
    'KEYWORDS',
    'RESERVED_WORD',      
    'NUMBER',
    'ARROW',
    'COMMA',
    'CROSS',           
    'LBRACE',     # '{'
    'RBRACE',    # '}'
    'LPAREN',     # '('
    'RPAREN',     # ')'
    'EQUAL',      # '='
)

# =====================================================================
# 2. REGULAR EXPRESSION RULES FOR SIMPLE TOKENS
# =====================================================================
# Direct string regex assignments map cleanly to the token names
t_EQUAL   = r'='
t_COMMA   = r','
t_LBRACE  = r'\{'
t_RBRACE  = r'\}'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_CROSS   = r'[X\*]'   # Matches 'X' or '*'
t_ARROW   = r'->'      # Automatically matches '->' as one unit

# Characters to completely skip over (whitespace and tabs)
t_ignore = ' \t'

# =====================================================================
# 3. REGULAR EXPRESSION RULES FOR COMPLEX TOKENS (WITH ACTIONS)
# =====================================================================

def t_NUMBER(t):
    r'\d+(\.\d+)?'     # Regex pattern in the docstring captures ints and floats
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

def t_IDENTIFIER(t):
    # Regex range explicitly allows standard characters plus 'δ' and 'Σ' natively
    r'[a-zA-Z_δΣ][a-zA-Z0-9_δΣ]*'
    if t.value in RESERVE_WORDS:
        t.type = 'RESERVED_WORD'
    elif t.value in KEYWORDS:
        t.type = 'KEYWORDS'
    return t

# Tracking line numbers automatically when newlines are parsed
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# =====================================================================
# 4. ERROR HANDLING RULE
# =====================================================================
def t_error(t):
    # If a minus sign wasn't followed by a '>' symbol to make an arrow
    if t.value[0] == '-':
        print(f"\nLexical Error: Isolated '-' symbol found instead of an arrow '->' on Line {t.lexer.lineno}")
    else:
        print(f"\nIllegal Character Error: '{t.value[0]}' on Line {t.lexer.lineno}")
    
    t.lexer.has_error = True
    t.lexer.skip(1)

# Build the dynamic lexer engine from the rules above
lexer = lex.lex()

# =====================================================================
# 5. USER INTERFACE DRIVER LOOP (Your Original Logic)
# =====================================================================
def run():
    while True:
        choice = input("\nChoose an option:\n1. Single-Line DFA Specification\n2. Multi-Line DFA Specification\n3. Exit\nEnter choice (1, 2, or 3): ")
        try:
            choice = int(choice)
        except ValueError:
            print("Invalid input. Please enter a number (1, 2, or 3).")
            continue
            
        if choice in (1, 2):
            print("\nEnter DFA Specification as 5-tuple M=({Q, Σ, δ, q0, F})")
            try:
                if choice == 1:
                    text = input()
                    if text.strip() in ('', 'exit'):
                        break
                else:
                    print("DFA name = ({Set of States}, {Input Symbols}, δ, starting state, {Final States}):")
                    print("Type 'exit' on a new line to finish input.")
                    lines = []
                    while True:
                        line = input()
                        if line.strip().lower() == 'exit':
                            break
                        lines.append(line)
                    text = '\n'.join(lines)
               
                # Feed the user text into the compiled PLY engine
                lexer.input(text)
                lexer.lineno = 1
                lexer.has_error = False
                
                # Retrieve tokens sequentially
                collected_tokens = []
                while True:
                    tok = lexer.token()
                    if not tok: 
                        break  # None signals the end of the input stream
                    collected_tokens.append(f"Token({tok.type}, {tok.value})")
                
                # Only display results if no lexical error tripped the has_error flag
                if not lexer.has_error:
                    print(f"\nSuccessfully generated {len(collected_tokens)} tokens:")
                    for token in collected_tokens:
                        print("  ", token)
                        
            except (KeyboardInterrupt, EOFError):
                break
        elif choice == 3:
            print("Exiting.")
            break

if __name__ == "__main__":
    run()
