from requests import Response

class TumblrRequest:
    # We love lying to type checkers :)
    def json_parse(self, response: Response) -> Response: ...
