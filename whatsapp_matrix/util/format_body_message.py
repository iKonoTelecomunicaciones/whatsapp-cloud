import yaml
import html


def format_body_message(yaml_message: dict) -> str:
    """Format the message body.

    The message body is formatted as a YAML block of code in HTML.

    Parameters:

    message: dict
        JSON object with the message body.
    """
    # format the message body
    formatted_body = f'<pre><code class="language-YAML">{yaml_message}</code></pre>'

    return formatted_body


def json_to_yaml(data: dict) -> str:
    """Convert JSON to YAML.

    Parameters:

    json_str: str
        JSON string to convert to YAML.
    """
    # Convert JSON to YAML
    yaml_str = yaml.dump(
        data=data,
        default_flow_style=False,
        allow_unicode=True,
        indent=2,
        sort_keys=False,
    )

    return yaml_str
