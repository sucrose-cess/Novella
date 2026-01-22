# Variables
default vnl_file_text = ""
default lexer_input = ""
default lexer_tokens = []
default lexer_error = ""
default lexer_ast_text = ""
default dialogue_lines = []
default dialogue_index = 0
default CHARACTERS = {}

# Utilities
init python:
    import os

    def _clean_text_for_display(s):
        if not s:
            return ""
        s = s.lstrip("\ufeff")
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        s = s.replace("\t", "    ")
        return s

    def load_vnl_file():
        global vnl_file_text
        try:
            raw = renpy.file("vnl/script.vnl").read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            vnl_file_text = _clean_text_for_display(raw)
        except Exception as e:
            vnl_file_text = ""
            renpy.log("Failed to load vnl/script.vnl: {}".format(e))

    def save_vnl_file(text):
        try:
            path = os.path.join("vnl", "script.vnl")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text or "")
        except Exception as e:
            renpy.log("Save failed: {}".format(e))

# Lexer
init python:

    KEYWORDS = {
        "SCENE": "KW_SCENE",
        "CHARACTER": "KW_CHARACTER",
        "FROM": "KW_FROM",
        "LEFT": "KW_LEFT",
        "RIGHT": "KW_RIGHT",
        "CENTER": "KW_CENTER",
        "TOP": "KW_TOP",
        "BOTTOM": "KW_BOTTOM",
        "HIDE": "KW_HIDE",
        "ENTER": "KW_ENTER",
        "EXIT": "KW_EXIT",
        "SOUND": "KW_SOUND",
        "PLAY": "KW_PLAY",
        "MUTE": "KW_MUTE",
        "RUN": "KW_RUN",
        "WALK": "KW_WALK",
        "CHOICE": "KW_CHOICE",
        "REPEAT": "KW_REPEAT"
    }

    # Keywords that should NOT absorb an identifier
    NO_IDENTIFIER_KEYWORDS = {
        "KW_FROM",
        "KW_LEFT", "KW_RIGHT", "KW_CENTER", "KW_TOP", "KW_BOTTOM",
        "KW_HIDE", "KW_ENTER", "KW_EXIT",
        "KW_RUN", "KW_WALK",
        "KW_CHOICE"
    }

    NOISE_WORDS = {"the", "a", "an", "to", "then", "at"}
    VALID_SYMBOLS = set("+-*/%=><!^_()[]:,.;~&")
    TWO_CHAR_OPS = {"==", "!=", ">=", "<="}

    class Token:
        def __init__(self, token_type, source, message=None):
            self.type = token_type
            self.source = source
            self.message = message

        def __str__(self):
            return "<{} {}>".format(self.type, self.source)

        __repr__ = __str__

    def lexer(text):
        i = 0
        tokens = []

        while i < len(text):
            c = text[i]

            if c.isspace():
                i += 1
                continue

            if c == "#":
                while i < len(text) and text[i] != "\n":
                    i += 1
                continue

            if text[i:i+3] == '"""':
                i += 3
                while i < len(text) and text[i:i+3] != '"""':
                    i += 1
                i += 3
                continue

            if c.isalpha():
                start = i
                i += 1
                while i < len(text) and (text[i].isalnum() or text[i] == "_"):
                    i += 1
                word = text[start:i]

                ttype = KEYWORDS.get(word.upper())
                if ttype is None:
                    if word.lower() in NOISE_WORDS:
                        continue
                    tokens.append(Token("IDENTIFIER", word))
                    continue

                token = Token(ttype, word)

                if ttype not in NO_IDENTIFIER_KEYWORDS:
                    while i < len(text) and text[i].isspace():
                        i += 1

                    start = i
                    while i < len(text) and (text[i].isalnum() or text[i] == "_"):
                        i += 1

                    identifier = text[start:i]
                    if identifier:
                        token.source = "{}".format(identifier)

                tokens.append(token)
                continue

            if c.isdigit():
                start = i
                while i < len(text) and text[i].isdigit():
                    i += 1
                tokens.append(Token("NUMBER", text[start:i]))
                continue

            if c == '"':
                i += 1
                start = i
                while i < len(text) and text[i] != '"':
                    i += 1
                if i >= len(text):
                    tokens.append(Token("ERROR", "Unterminated string"))
                    break
                tokens.append(Token("STRING", text[start:i]))
                i += 1
                continue

            if text[i:i+2] in TWO_CHAR_OPS:
                tokens.append(Token("SYMBOL", text[i:i+2]))
                i += 2
                continue

            if c in VALID_SYMBOLS:
                tokens.append(Token("SYMBOL", c))
                i += 1
                continue

            tokens.append(Token("ERROR", "Invalid character"))
            i += 1

        return tokens

# Lex + Parse Wrapper
init python:
    def lex_and_parse():
        global lexer_tokens, lexer_error, dialogue_lines

        source = lexer_input.strip() or vnl_file_text
        lexer_tokens = lexer(source)
        dialogue_lines = source.splitlines()
        lexer_error = ""

# Editor Screen
screen multiline_editor():
    modal True
    default temp_text = lexer_input or vnl_file_text

    frame:
        xalign 0.5
        yalign 0.5
        xsize 1300
        ysize 650
        xpadding 70
        ypadding 60

        vbox:
            spacing 30

            viewport:
                draggable True
                mousewheel True
                ysize 450

                input:
                    value ScreenVariableInputValue("temp_text")
                    multiline True
                    length 20000
                    color "#FFFFFF"
                    size 25

            hbox:
                spacing 20
                xalign 1.0

                textbutton "Cancel":
                    action Hide("multiline_editor")

                textbutton "Save":
                    action [
                        SetVariable("lexer_input", temp_text),
                        Function(save_vnl_file, temp_text),
                        Function(lex_and_parse),
                        Hide("multiline_editor")
                    ]

# Lexer Output Screen
screen lexer_output_screen():

    vbox:
        spacing 10
        xalign 0.5
        yalign 0.5

        hbox:
            spacing 40

            # Code Sample
            vbox:
                spacing 10

                text "Code Sample" bold True size 32

                viewport:
                    xsize 500
                    ysize 460
                    draggable True
                    mousewheel True

                    text lexer_input.strip() or vnl_file_text size 30

                textbutton "EDIT":
                    action Show("multiline_editor")

                textbutton "SEE TOKENS":
                    action [ Function(lex_and_parse), Function(renpy.restart_interaction) ]

            # Token Table
            vbox:
                spacing 10

                text "Tokens" bold True size 32

                viewport:
                    xsize 460
                    ysize 460
                    draggable True
                    mousewheel True

                    vbox:
                        spacing 5

                        # HEADER
                        hbox:
                            spacing 10
                            frame:
                                xsize 200
                                text "Token Type" bold True color "#3f3b27" size 22 xalign 0.5 yalign 0.5
                            frame:
                                xsize 260
                                text "Value" bold True color "#3f3b27" size 22 xalign 0.5 yalign 0.5

                        # TOKENS
                        for t in lexer_tokens:
                            hbox:
                                spacing 10
                                frame:
                                    xsize 200
                                    text ("Identifier" if t.type == "IDENTIFIER" else t.type) color "#e2c59d" size 22 xalign 0.5 yalign 0.5
                                frame:
                                    xsize 260
                                    text t.source color "#f6c785" size 22 xalign 0.5 yalign 0.5

# Main
label start:
    $ load_vnl_file()
    $ lex_and_parse()
    show screen lexer_output_screen

    image saveload_ground = "gui/overlay/game_menu.png"
    show saveload_ground
    $ renpy.pause()
    return
