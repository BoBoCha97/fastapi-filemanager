from pathlib import Path

app_root_path = Path(__file__).parent.resolve()

app_static_dir = app_root_path / 'static'

app_html_dir = app_static_dir / 'html'

html_template_path = app_html_dir / 'home.html'

with open(html_template_path) as f:
    html_template = f.read()


if __name__ == '__main__':
    print(app_root_path)
