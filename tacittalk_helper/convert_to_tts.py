import re
import html

def convert_to_tts(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Remove <pre> blocks that are large numeric tables/grids
    # These are blocks with many lines of mostly numbers, spaces, and ¯
    def is_numeric_grid(block):
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        if len(lines) < 4:
            return False
        grid_lines = 0
        for line in lines:
            cleaned = line.replace('¯', '').replace(' ', '').replace('.', '')
            if cleaned and all(c in '0123456789' for c in cleaned):
                grid_lines += 1
        return grid_lines >= 3

    def replace_pre(match):
        content = match.group(1)
        if is_numeric_grid(content):
            # Check if there's a label line before the grid (like "Rº.=G S")
            lines = [l for l in content.split('\n') if l.strip()]
            label_lines = []
            for line in lines:
                cleaned = line.strip().replace('¯', '').replace(' ', '').replace('.', '')
                if cleaned and all(c in '0123456789' for c in cleaned):
                    break
                label_lines.append(line.strip())
            if label_lines:
                return '\n[Table: ' + ' ; '.join(label_lines) + ' — numeric table omitted]\n'
            return '\n[Numeric table omitted]\n'
        return content

    text = re.sub(r'<pre>(.*?)</pre>', replace_pre, text, flags=re.DOTALL)

    # Remove the big Table A.1 (the bordered function reference table)
    text = re.sub(
        r'<table border=1 cellspacing=0.*?</table>\s*<p align=center>Table A\.1</p>',
        '\n[Table A.1: APL function symbols showing monadic and dyadic forms for '
        'plus, minus, times, divide, ceiling/maximum, floor/minimum, '
        'power/exponential, logarithm, and magnitude/remainder — table omitted]\n',
        text, flags=re.DOTALL
    )

    # Handle <sup> before stripping tags: X<sup>N</sup> → "X to the N"
    text = re.sub(r'(\w)<sup>([^<]+)</sup>', r'\1 to the \2', text)
    text = re.sub(r'<sup>([^<]+)</sup>', r' to the \1', text)

    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities
    text = html.unescape(text)

    # APL symbol replacements (order matters for some)
    apl_replacements = [
        ('º.×', ' outer-product-times '),
        ('º.+', ' outer-product-plus '),
        ('º.*', ' outer-product-power '),
        ('º.=', ' outer-product-equals '),
        ('º.⌈', ' outer-product-maximum '),
        ('º.⌊', ' outer-product-minimum '),
        ('º.-', ' outer-product-minus '),
        ('º.≥', ' outer-product-greater-or-equal '),
        ('º.≤', ' outer-product-less-or-equal '),
        ('+/', 'plus-reduce '),
        ('×/', 'times-reduce '),
        ('⌈/', 'max-reduce '),
        ('÷/', 'divide-reduce '),
        ('←', ' gets '),
        ('∇', ' del '),
        ('↔', ' corresponds to '),
        ('×', ' times '),
        ('÷', ' divide '),
        ('⌈', ' ceiling '),
        ('⌊', ' floor '),
        ('⍟', ' log '),
        ('≤', ' less-or-equal '),
        ('≥', ' greater-or-equal '),
        ('≠', ' not-equal '),
        ('¯', ' negative '),
    ]

    for old, new in apl_replacements:
        text = text.replace(old, new)

    # Clean up remaining entities that unescape might have missed
    text = text.replace('\xa0', ' ')  # non-breaking space

    # Remove the javascript/metadata footer
    text = re.sub(r'document\.write\(.*?\)', '', text, flags=re.DOTALL)
    text = re.sub(r'created:.*?updated:.*?\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', '', text, flags=re.DOTALL)

    # Collapse multiple blank lines into at most two
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove leading/trailing whitespace on each line, but preserve blank lines
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        cleaned_lines.append(stripped)
    text = '\n'.join(cleaned_lines)

    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)

    # Remove leading blank lines
    text = text.lstrip('\n')

    # Final trim
    text = text.strip() + '\n'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f"Written TTS version to {output_path}")
    print(f"Size: {len(text)} chars, {text.count(chr(10))} lines")


if __name__ == '__main__':
    convert_to_tts(
        '/home/cph/vibing/tacittalk_helper/algebra1.htm',
        '/home/cph/vibing/tacittalk_helper/algebra1_tts.txt'
    )
