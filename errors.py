class APIError(Exception): 
    def __init__(self,message,status_code): 
        super().__init__(message)
        self.message = message 
        self.status_code = status_code 

class InvalidInputError(APIError): 
    def __init__(self,message): 
        super().__init__(message,400)

class NotFoundError(APIError): 
    def __init__(self,message): 
        super().__init__(message,404)

class RuleViolationError(APIError): 
    def __init__(self,message): 
        super().__init__(message, 409)

def register_error_handlers(app): 
    @app.errorhandler (APIError)
    def handle_api_error(error): 
        return {"error": error.message}, error.status_code 
