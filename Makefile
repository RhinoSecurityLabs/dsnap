requirements:
	poetry export -f requirements.txt -o requirements.txt

flake8:
	flake8 pysnap

lint: flake8 mypy

stubgen:
	test -d stubs || stubgen -p boto3 -p botocore -o stubs

mypy: stubgen
	export MYPYPATH="${PWD}/stubs" && mypy pysnap

clean:
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	rm -rf out/
	rm -rf ./**/**/__pycache__/

test:
	pytest ./tests
