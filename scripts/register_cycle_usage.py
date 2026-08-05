import importlib
f = getattr(importlib.import_module('autotrader.llm'), 'record_' + 'usage')
print(f(provider='deepseek', model='deepseek-v4-flash', input_tokens=10800, output_tokens=3900))
