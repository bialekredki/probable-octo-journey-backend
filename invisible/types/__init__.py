from pydantic import constr



TinyURL = constr(min_length=16, max_length=16, strict=True) # TODO: Add regex