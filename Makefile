flake8:
	flake8 dsnap --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 dsnap --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

lint: flake8 mypy

mypy:
	mypy dsnap

clean:
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	rm -rf out/
	rm -rf ./**/**/__pycache__/

test:
	pytest ./tests
