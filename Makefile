IMAGE ?= output.img

flake8:
	flake8 dsnap --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 dsnap --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

lint: flake8 mypy

stubgen:
	test -d stubs || stubgen --include-private -o stubs -p boto3 -p stubs.boto3.resources.base -p botocore -p jmespath

mypy: stubgen
	MYPYPATH="${PWD}/stubs" mypy --show-error-codes dsnap

clean:
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	rm -rf out/
	rm -rf ./**/**/__pycache__/

docker/build:
	docker build -f Dockerfile.mount -t dsnap-mount .

docker/run:
	docker run -it -v "${PWD}/${IMAGE}:/disks/${IMAGE}" -w /disks dsnap-mount --ro -a "${IMAGE}" -m /dev/sda1:/

test:
	pytest ./tests
