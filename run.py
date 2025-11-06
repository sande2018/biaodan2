from app import app, db
from app.models import Form, FormField, FormSubmission, CDK

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Form': Form, 'FormField': FormField, 'FormSubmission': FormSubmission, 'CDK': CDK}

if __name__ == '__main__':
    app.run(debug=True)
