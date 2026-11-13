from enum import Enum
import string

# CONSTANTS
LETTERS = string.ascii_letters + '_' + 'δ' + 'Σ'
ALPHANUMERIC = LETTERS + string.digits 
NUMBERS = r'0123456789'

# KEYWORDS & RESERVED WORDS 
RESERVE_WORDS = [
    'WHILE', 'IF', 'ELSE', 'FOR', 'RETURN', 'FUNCTION', 'VAR', 'LET', 'CONST'
]
KEYWORDS = [
    'Q', 'Σ', 'F', 'δ', 'q0', 'delta', 'DELTA'
]

# TokenTypes
class TT(Enum):
    T_Identifier = 'IDENTIFIER'
    T_Keyword = 'KEYWORDS'
    T_Reserved = 'RESERVED WORD'        
    T_Number = 'NUMBER'
    T_Arrow = 'ARROW'
    T_Comma = 'COMMA'
    T_Cross = 'CROSS'             
    T_OpenBracket = 'LBRACE'    # '{'
    T_CloseBracket = 'RBRACE'   # '}'
    T_LPAREN = 'LPAREN'         # '('
    T_RPAREN = 'RPAREN'         # ')'
    T_EQUAL = 'EQUAL'           # '='

# Position tracking block for error handling
class PositionInfo:
    def __init__(self, ln):
        self.ln = ln

# Error handling
class Error:
    def __init__(self, posStart, errorName, details):
        self.posStart = posStart
        self.errorName = errorName
        self.details = details

    def __repr__(self):
        return f"{self.errorName}: {self.details}\nLine {self.posStart.ln + 1}"

# Tokens
class Token:
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __repr__(self):
        if self.value is not None:
            return f"Token({self.type}, {self.value})"
        return f"Token({self.type})"

# Lexer
class Lexer:
    def __init__(self, text):
        self.text = text
        self.position = -1 
        self.ln = 0                # Track line changes
        self.current_char = None
        self.advance()

    def advance(self):
        self.position += 1
        if self.current_char == '\n':
            self.ln += 1 
        self.current_char = self.text[self.position] if self.position < len(self.text) else None  

    def tokenizer(self):
        tokens = []
        while self.current_char != None:
            if self.current_char.isspace(): 
               self.advance()
            elif self.current_char == '=':
                tokens.append(Token(TT.T_EQUAL.value))
                self.advance()
            elif self.current_char == ',':
                tokens.append(Token(TT.T_Comma.value))
                self.advance()
            elif self.current_char == '{':
                tokens.append(Token(TT.T_OpenBracket.value))
                self.advance()
            elif self.current_char == '}':
                tokens.append(Token(TT.T_CloseBracket.value))
                self.advance()
            elif self.current_char == '(':
                tokens.append(Token(TT.T_LPAREN.value))
                self.advance()
            elif self.current_char == ')':
                tokens.append(Token(TT.T_RPAREN.value))
                self.advance()
            # Restored 'X' along with '*' for set cross products (e.g., Q X Σ)
            elif self.current_char in ('X', '*'):
                tokens.append(Token(TT.T_Cross.value, self.current_char))
                self.advance()
            elif self.current_char == '-':
                self.advance()
                if self.current_char == '>':
                    tokens.append(Token(TT.T_Arrow.value))
                    self.advance()
                else:
                    pos = PositionInfo(self.ln)
                    return [], Error(pos, "Lexical Error", "Isolated '-' symbol found instead of an arrow '->'")
            elif self.current_char in NUMBERS:
                tokens.append(self.makeNumber())
            elif self.current_char in LETTERS:
                tokens.append(self.makeIdentifier())
            else:
                pos = PositionInfo(self.ln)
                char = self.current_char
                self.advance()
                return [], Error(pos, "Illegal Character Error", f"'{char}'")
                
        return tokens, None 

    def makeNumber(self):
        numString = ''
        dotCount = 0

        while self.current_char != None and (self.current_char in NUMBERS or self.current_char == '.'):
            if self.current_char == '.':
                if dotCount == 1: 
                    break
                dotCount += 1
                numString += '.'
            else:
                numString += self.current_char
            self.advance()

        if dotCount == 0: 
            return Token(TT.T_Number.value, int(numString))
        else: 
            return Token(TT.T_Number.value, float(numString))

    def makeIdentifier(self):
        idString = ''
        while self.current_char != None and (self.current_char in ALPHANUMERIC):
            idString += self.current_char
            self.advance()
            
        if idString in RESERVE_WORDS:
            return Token(TT.T_Reserved.value, idString)
        elif idString in KEYWORDS:
            return Token(TT.T_Keyword.value, idString)
            
        return Token(TT.T_Identifier.value, idString)

# Run
def run():
    while True:
        prompt = (
            "\nChoose an option:\n"
            "1. Single-Line DFA Specification\n"
            "2. Multi-Line DFA Specification\n"
            "3. Exit\n"
            "Enter choice (1, 2, or 3): "
        )
        choice = input(prompt)
        try:
            choice = int(choice)
        except ValueError:
            print("Invalid input. Please enter a number (1, 2, or 3).")
            continue
            
        if choice == 3:
            break
            
        if choice in (1, 2):
            print("\nEnter DFA Specification:")
            try:
                if choice == 1:
                    text = input()
                    if text.strip() in ('', 'exit'):
                        break
                else:
                    print("Type 'exit' on a new line to finish input.")
                    lines = []
                    while True:
                        line = input()
                        if line.strip().lower() == 'exit':
                            break
                        lines.append(line)
                    text = '\n'.join(lines)
               
                lexer = Lexer(text)
                tokens, error = lexer.tokenizer()
            
                if error:
                    print("\n", error)
                else:
                    print(f"\nSuccessfully generated {len(tokens)} tokens:")
                    for token in tokens:
                        print("  ", token)
            except (KeyboardInterrupt, EOFError):
                break

if __name__ == "__main__":
    run()