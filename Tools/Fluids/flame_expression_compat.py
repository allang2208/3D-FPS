"""Keep sine-hash random fractions nonnegative on Niagara CPU VectorVM."""

def nonnegative_random_hashes(value):
    # VectorVM frac truncates toward zero; HLSL frac floors. Sine hashes span
    # both signs, so take abs BEFORE frac without changing the emitter graph.
    cursor = 0
    while (start := value.find('frac(sin(', cursor)) >= 0:
        inner = start + len('frac(')
        depth, end = 1, inner
        while end < len(value) and depth:
            if value[end] == '(':
                depth += 1
            elif value[end] == ')':
                depth -= 1
            end += 1
        if depth:
            raise ValueError('Unbalanced flame random expression')
        replacement = 'frac(abs(' + value[inner:end-1] + '))'
        value = value[:start] + replacement + value[end:]
        cursor = start + len(replacement)
    return value
