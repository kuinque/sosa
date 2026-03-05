.PHONY: generate run up down clean

generate:
	bash generate.sh

run: generate
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

up:
	docker compose up --build

down:
	docker compose down -v

clean:
	rm -rf app/generated
