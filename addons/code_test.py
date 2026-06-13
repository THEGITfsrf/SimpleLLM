description = "compiles and tests code for errors"
args = {
    "code": {
        "type": "string",
        "description": "Python code to compile and test"
    }
}
required = ["code"]

def main(code):
    # First, compile the code to check for syntax errors
    try:
        compiled = compile(code, '<test>', 'exec')
    except SyntaxError as e:
        return False, f"Syntax Error: {e.msg} at line {e.lineno}"
    
    # Create a test function to run
    def run_tests(code):
        namespace = {"__builtins__": {}}
        try:
            exec(compile(code, '<test>', 'exec'), namespace)
            return True, "Tests passed"
        except Exception as e:
            return False, f"Runtime Error: {e}"
    
    return run_tests(code)
