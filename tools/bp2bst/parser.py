"""Recursive descent parser for Android.bp Blueprint format.

Handles:
- Module definitions: cc_library { name: "foo", srcs: ["a.c"], ... }
- Variable assignments: my_var = ["a", "b"]
- Variable references: srcs: my_var
- List concatenation: my_var + ["c"]
- Nested maps: arch: { arm: { cflags: [...] } }
- select() expressions
- // and /* */ comments
- += assignments
"""

import re
from typing import Optional
from . import ast


class ParseError(Exception):
    def __init__(self, message, line=0, col=0):
        self.line = line
        self.col = col
        super().__init__(f"line {line}, col {col}: {message}")


class Token:
    __slots__ = ("type", "value", "line", "col")

    def __init__(self, type_, value, line=0, col=0):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, L{self.line})"


# Token types
TOK_IDENT = "IDENT"
TOK_STRING = "STRING"
TOK_INT = "INT"
TOK_LBRACE = "LBRACE"    # {
TOK_RBRACE = "RBRACE"    # }
TOK_LBRACKET = "LBRACKET" # [
TOK_RBRACKET = "RBRACKET" # ]
TOK_LPAREN = "LPAREN"    # (
TOK_RPAREN = "RPAREN"    # )
TOK_COLON = "COLON"      # :
TOK_COMMA = "COMMA"      # ,
TOK_EQUALS = "EQUALS"    # =
TOK_PLUS = "PLUS"        # +
TOK_PLUSEQ = "PLUSEQ"     # +=
TOK_EOF = "EOF"

# Reserved keywords that look like identifiers
KEYWORDS = {"true", "false", "select", "unset"}


class Lexer:
    """Tokenizer for Android.bp files."""

    def __init__(self, text: str, filename: str = "<input>"):
        self.text = text
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1

    def _advance(self, n=1):
        for i in range(n):
            if self.pos < len(self.text):
                if self.text[self.pos] == "\n":
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
                self.pos += 1

    def _peek(self) -> Optional[str]:
        if self.pos < len(self.text):
            return self.text[self.pos]
        return None

    def _peek2(self) -> Optional[str]:
        if self.pos + 1 < len(self.text):
            return self.text[self.pos + 1]
        return None

    def _skip_whitespace_and_comments(self):
        while self.pos < len(self.text):
            c = self.text[self.pos]

            # Whitespace
            if c in " \t\r\n":
                self._advance()
                continue

            # Line comment
            if c == "/" and self._peek2() == "/":
                while self.pos < len(self.text) and self.text[self.pos] != "\n":
                    self._advance()
                continue

            # Block comment
            if c == "/" and self._peek2() == "*":
                self._advance(2)
                while self.pos < len(self.text):
                    if self.text[self.pos] == "*" and self._peek2() == "/":
                        self._advance(2)
                        break
                    self._advance()
                continue

            break

    def _read_string(self) -> str:
        """Read a double-quoted string, handling escape sequences."""
        assert self.text[self.pos] == '"'
        self._advance()  # skip opening quote
        result = []
        while self.pos < len(self.text):
            c = self.text[self.pos]
            if c == "\\":
                self._advance()
                if self.pos < len(self.text):
                    esc = self.text[self.pos]
                    if esc == "n":
                        result.append("\n")
                    elif esc == "t":
                        result.append("\t")
                    elif esc == "\\":
                        result.append("\\")
                    elif esc == '"':
                        result.append('"')
                    else:
                        result.append(esc)
                    self._advance()
            elif c == '"':
                self._advance()  # skip closing quote
                return "".join(result)
            else:
                result.append(c)
                self._advance()
        raise ParseError("Unterminated string", self.line, self.col)

    def _read_ident(self) -> str:
        """Read an identifier: [a-zA-Z_][a-zA-Z0-9_]*."""
        start = self.pos
        while self.pos < len(self.text) and (
            self.text[self.pos].isalnum() or self.text[self.pos] == "_"
        ):
            self._advance()
        return self.text[start : self.pos]

    def _read_int(self) -> int:
        """Read an integer literal."""
        start = self.pos
        if self.text[self.pos] == "-":
            self._advance()
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self._advance()
        return int(self.text[start : self.pos])

    def next_token(self) -> Token:
        self._skip_whitespace_and_comments()

        if self.pos >= len(self.text):
            return Token(TOK_EOF, "", self.line, self.col)

        line, col = self.line, self.col
        c = self.text[self.pos]

        if c == '"':
            value = self._read_string()
            return Token(TOK_STRING, value, line, col)

        if c.isalpha() or c == "_":
            value = self._read_ident()
            return Token(TOK_IDENT, value, line, col)

        if c.isdigit() or (c == "-" and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
            value = self._read_int()
            return Token(TOK_INT, value, line, col)

        if c == "{":
            self._advance()
            return Token(TOK_LBRACE, "{", line, col)
        if c == "}":
            self._advance()
            return Token(TOK_RBRACE, "}", line, col)
        if c == "[":
            self._advance()
            return Token(TOK_LBRACKET, "[", line, col)
        if c == "]":
            self._advance()
            return Token(TOK_RBRACKET, "]", line, col)
        if c == "(":
            self._advance()
            return Token(TOK_LPAREN, "(", line, col)
        if c == ")":
            self._advance()
            return Token(TOK_RPAREN, ")", line, col)
        if c == ":":
            self._advance()
            return Token(TOK_COLON, ":", line, col)
        if c == ",":
            self._advance()
            return Token(TOK_COMMA, ",", line, col)
        if c == "+":
            self._advance()
            if self._peek() == "=":
                self._advance()
                return Token(TOK_PLUSEQ, "+=", line, col)
            return Token(TOK_PLUS, "+", line, col)
        if c == "=":
            self._advance()
            return Token(TOK_EQUALS, "=", line, col)

        raise ParseError(f"Unexpected character: {c!r}", line, col)

    def tokenize(self) -> list:
        """Tokenize the entire input and return a list of tokens."""
        tokens = []
        while True:
            tok = self.next_token()
            tokens.append(tok)
            if tok.type == TOK_EOF:
                break
        return tokens


class Parser:
    """Recursive descent parser for Android.bp files."""

    def __init__(self, text: str, filename: str = "<input>"):
        self.lexer = Lexer(text, filename)
        self.tokens = self.lexer.tokenize()
        self.pos = 0
        self.filename = filename

    def _peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TOK_EOF, "", 0, 0)

    def _advance(self) -> Token:
        tok = self._peek()
        self.pos += 1
        return tok

    def _expect(self, type_: str) -> Token:
        tok = self._advance()
        if tok.type != type_:
            raise ParseError(
                f"Expected {type_}, got {tok.type} ({tok.value!r})",
                tok.line, tok.col,
            )
        return tok

    def _at(self, type_: str) -> bool:
        return self._peek().type == type_

    def _match(self, type_: str) -> Optional[Token]:
        if self._at(type_):
            return self._advance()
        return None

    def parse(self) -> ast.File:
        """Parse the entire file and return an AST File node."""
        file = ast.File(name=self.filename)
        while not self._at(TOK_EOF):
            defn = self._parse_definition()
            if defn is not None:
                file.defs.append(defn)
        return file

    def _parse_definition(self):
        """Parse a top-level definition: module or assignment."""
        tok = self._peek()

        if tok.type != TOK_IDENT:
            raise ParseError(
                f"Expected identifier at top level, got {tok.type} ({tok.value!r})",
                tok.line, tok.col,
            )

        # Look ahead to determine if this is an assignment or a module
        # Assignment: ident = expr  or  ident += expr
        # Module: ident { ... }
        next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else Token(TOK_EOF, "", 0, 0)

        if next_tok.type in (TOK_EQUALS, TOK_PLUSEQ):
            return self._parse_assignment()
        elif next_tok.type == TOK_LBRACE:
            return self._parse_module()
        else:
            raise ParseError(
                f"Expected '=', '+=', or '{{' after identifier '{tok.value}', got {next_tok.type}",
                next_tok.line, next_tok.col,
            )

    def _parse_assignment(self) -> ast.Assignment:
        name_tok = self._expect(TOK_IDENT)
        if self._at(TOK_PLUSEQ):
            assigner_tok = self._advance()
            assigner = "+="
        else:
            assigner_tok = self._expect(TOK_EQUALS)
            assigner = "="
        value = self._parse_expression()
        return ast.Assignment(name=name_tok.value, value=value, assigner=assigner)

    def _parse_module(self) -> ast.Module:
        type_tok = self._expect(TOK_IDENT)
        properties = self._parse_map_body()
        return ast.Module(type=type_tok.value, properties=properties)

    def _parse_map_body(self) -> list:
        """Parse { prop: val, prop: val, ... } and return list of Property."""
        self._expect(TOK_LBRACE)
        properties = []
        while not self._at(TOK_RBRACE) and not self._at(TOK_EOF):
            prop = self._parse_property()
            properties.append(prop)
            self._match(TOK_COMMA)  # optional trailing comma
        self._expect(TOK_RBRACE)
        return properties

    def _parse_property(self) -> ast.Property:
        name_tok = self._expect(TOK_IDENT)
        self._expect(TOK_COLON)
        value = self._parse_expression()
        return ast.Property(name=name_tok.value, value=value)

    def _parse_expression(self) -> ast.Expression:
        """Parse an expression, handling + concatenation."""
        left = self._parse_primary()

        while self._at(TOK_PLUS):
            self._advance()  # consume +
            right = self._parse_primary()
            left = ast.OperatorExpr(left=left, op="+", right=right)

        return left

    def _parse_primary(self) -> ast.Expression:
        """Parse a primary expression."""
        tok = self._peek()

        if tok.type == TOK_STRING:
            self._advance()
            return ast.StringExpr(value=tok.value)

        if tok.type == TOK_INT:
            self._advance()
            return ast.IntExpr(value=tok.value)

        if tok.type == TOK_LBRACKET:
            return self._parse_list()

        if tok.type == TOK_LBRACE:
            props = self._parse_map_body()
            return ast.MapExpr(properties=props)

        if tok.type == TOK_IDENT:
            if tok.value == "true":
                self._advance()
                return ast.BoolExpr(value=True)
            if tok.value == "false":
                self._advance()
                return ast.BoolExpr(value=False)
            if tok.value == "unset":
                self._advance()
                return ast.StringExpr(value="__unset__")
            if tok.value == "select":
                return self._parse_select()

            # Check if this is a module (ident followed by {) — shouldn't
            # happen inside expressions, but just in case treat as variable ref
            self._advance()
            return ast.VariableRef(name=tok.value)

        raise ParseError(
            f"Unexpected token in expression: {tok.type} ({tok.value!r})",
            tok.line, tok.col,
        )

    def _parse_list(self) -> ast.ListExpr:
        """Parse [ expr, expr, ... ]."""
        self._expect(TOK_LBRACKET)
        values = []
        while not self._at(TOK_RBRACKET) and not self._at(TOK_EOF):
            values.append(self._parse_expression())
            self._match(TOK_COMMA)  # optional trailing comma
        self._expect(TOK_RBRACKET)
        return ast.ListExpr(values=values)

    def _parse_select(self) -> ast.SelectExpr:
        """Parse select(condition, { case: value, ... })."""
        self._expect(TOK_IDENT)  # "select"
        self._expect(TOK_LPAREN)

        # Parse condition: func_name("arg1", "arg2", ...)
        func_name_tok = self._expect(TOK_IDENT)
        self._expect(TOK_LPAREN)
        func_args = []
        while not self._at(TOK_RPAREN) and not self._at(TOK_EOF):
            arg_tok = self._expect(TOK_STRING)
            func_args.append(arg_tok.value)
            self._match(TOK_COMMA)
        self._expect(TOK_RPAREN)

        self._expect(TOK_COMMA)

        # Parse cases: { pattern: value, ... }
        self._expect(TOK_LBRACE)
        cases = []
        while not self._at(TOK_RBRACE) and not self._at(TOK_EOF):
            # Pattern can be string, "default", or "any" identifier
            if self._at(TOK_STRING):
                pattern_tok = self._advance()
                patterns = [ast.StringExpr(pattern_tok.value)]
            elif self._at(TOK_IDENT):
                pattern_tok = self._advance()
                patterns = [ast.StringExpr(pattern_tok.value)]
            elif self._at(TOK_LPAREN):
                # Tuple pattern: ("val1", "val2")
                self._advance()
                patterns = []
                while not self._at(TOK_RPAREN):
                    p = self._expect(TOK_STRING)
                    patterns.append(ast.StringExpr(p.value))
                    self._match(TOK_COMMA)
                self._expect(TOK_RPAREN)
            else:
                raise ParseError(
                    f"Expected pattern in select case, got {self._peek().type}",
                    self._peek().line, self._peek().col,
                )

            self._expect(TOK_COLON)
            value = self._parse_expression()
            cases.append((patterns, value))
            self._match(TOK_COMMA)

        self._expect(TOK_RBRACE)
        self._expect(TOK_RPAREN)

        return ast.SelectExpr(
            func_name=func_name_tok.value,
            func_args=func_args,
            cases=cases,
        )


def parse_file(filepath: str) -> ast.File:
    """Parse an Android.bp file and return an AST."""
    with open(filepath, "r") as f:
        text = f.read()
    parser = Parser(text, filename=filepath)
    return parser.parse()


def parse_string(text: str, filename: str = "<string>") -> ast.File:
    """Parse an Android.bp string and return an AST."""
    parser = Parser(text, filename=filename)
    return parser.parse()
