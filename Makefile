.PHONY: help up down logs unit grade grade-ref validate scoring-tests clean

help:
	@grep -E '^[a-z-]+:' Makefile | sed 's/:.*//' | tr '\n' ' '; echo

up:            ## start the stack from environment/
	cd environment && docker compose up -d --build --wait

down:
	cd environment && docker compose down -v --remove-orphans

logs:
	cd environment && docker compose logs -f order-service

unit:          ## java unit tests on the shipped code
	cd environment/order-service && mvn -q test

grade:         ## grade the shipped code (expected: FAIL)
	cd grader && python run_grader.py

grade-ref:     ## grade the reference patch (expected: PASS)
	cd grader && python run_grader.py --patch ../patches/reference.patch

validate:      ## run every expected case through the grader
	cd grader && python validate_grader.py

scoring-tests: ## grader unit tests, no docker
	cd grader && python -m pytest tests -q

clean:
	rm -rf environment/order-service/target results/runs results/last-run
	find . -name __pycache__ -type d -exec rm -rf {} +
