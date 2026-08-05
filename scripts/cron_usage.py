from autotrader.llm import record_usage
print(record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=9000, output_tokens=1900))
