# Banner
BANNERSTAMP	= .banner_shown

# Program names
DISP_NAME	= RAG_Against_the_Machine
NAME		= src.__main__
FOLDER		= src.

# Lint targets
FLAKE8_TGT	= src/
MYPY_TGT	= src/

#Colors
LIGHT_GRAY		= \033[2m
ORANGE			= \033[1;33m
BLACK			= \033[1;30m
DARK_GRAY		= \033[1;90m
RED				= \033[1;31m
BRIGHT_RED		= \033[1;91m
GREEN			= \033[1;32m
BRIGHT_GREEN	= \033[1;92m
YELLOW			= \033[1;93m
BLUE			= \033[1;34m
BRIGHT_BLUE		= \033[1;94m
MAGENTA			= \033[1;35m
BRIGHT_PURPLE	= \033[1;95m
CYAN			= \033[1;96m
WHITE			= \033[1;97m
BROWN			= \33[1;38;2;160;120;80m
BLUE42			= \33[1;38;2;16;32;96m
WHITE_ON_BLUE42	= \33[0;97m\33[0;48;2;16;32;96m
RESET			= \033[0m

#Format
BOLD		= \033[1m
ITALIC		= \033[3m
UNDERLINE	= \033[4m
CROSS		= \033[9m
FLASH		= \033[5m
NEGATIVE	= \033[7m

# Rules
${BANNERSTAMP}:
				@clear
				@echo "${BOLD}"
				@echo "${BROWN} ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
				@echo "${BROWN} ║${BLUE42}  ◢◤ ◤█${BRIGHT_PURPLE}       ▁▁▁▁  ▁▁▁   ▁▁▁▁▁▁   ▁▁▁               ▁▁           ▁▁     ▁▁  ▁▁            ▁▁  ▁▁▁           ▁▁    ▁▁            ${BLUE42}█◥ ◥◣  ${BROWN}║"
				@echo "${BROWN} ║${BLUE42} ◢◤  ◢◤${BRIGHT_PURPLE}      ╱ ▁▁ ╲╱   │ ╱ ▁▁▁▁╱  ╱   │ ▁▁▁▁▁▁▁▁▁▁▁▁╱▁╱▁▁▁  ▁▁▁▁▁╱ ╱▁   ╱ ╱▁╱ ╱▁  ▁▁▁     ╱  │╱  ╱▁▁▁▁▁▁▁▁▁▁╱ ╱▁  ╱▁╱▁▁▁  ▁▁▁    ${BLUE42}◥◣  ◥◣ ${BROWN}║"
				@echo "${BROWN} ║${BLUE42} ███ █◢${BRIGHT_PURPLE}     ╱ ╱▁╱ ╱ ╱│ │╱ ╱ ▁▁   ╱ ╱│ │╱ ▁▁  ╱ ▁▁  ╱ ╱ ▁▁ ╲╱ ▁▁▁╱ ▁▁╱  ╱ ▁▁╱ ▁▁ ╲╱ ▁ ╲   ╱ ╱│▁╱ ╱ ▁▁  ╱ ▁▁▁╱ ▁▁ ╲╱ ╱ ▁▁ ╲╱ ▁ ╲   ${BLUE42}◣█ ███ ${BROWN}║"
				@echo "${BROWN} ║${BLUE42}   █   ${BRIGHT_PURPLE}    ╱ ▁  ▁╱ ▁▁▁ ╱ ╱▁╱ ╱  ╱ ▁▁▁ ╱ ╱▁╱ ╱ ╱▁╱ ╱ ╱ ╱ ╱ ╱▁▁  ╱ ╱▁   ╱ ╱▁╱ ╱ ╱ ╱  ▁▁╱  ╱ ╱  ╱ ╱ ╱▁╱ ╱ ╱▁▁╱ ╱ ╱ ╱ ╱ ╱ ╱ ╱  ▁▁╱   ${BLUE42}   █   ${BROWN}║"
				@echo "${BROWN} ║${BLUE42}  2026 ${BRIGHT_PURPLE}   ╱▁╱ │▁╱▁╱  │▁╲▁▁▁▁╱  ╱▁╱  │▁╲▁▁  ╱╲▁▁▁▁╱▁╱▁╱ ╱▁╱▁▁▁▁╱╲▁▁╱   ╲▁▁╱▁╱ ╱▁╱╲▁▁▁╱  ╱▁╱  ╱▁╱╲▁▁▁▁╱╲▁▁▁╱▁╱ ╱▁╱▁╱▁╱ ╱▁╱╲▁▁▁╱    ${BLUE42} 2026  ${BROWN}║"
				@echo "${BROWN} ║${BLUE42}       ${BRIGHT_PURPLE}                              ╱▁▁▁▁╱                                                                                      ${BLUE42}       ${BROWN}║"
				@echo "${BROWN} ║${BLUE42}  OPR                                                     ${CYAN}42 ${BROWN}- ${BRIGHT_PURPLE}orobert ${BROWN}- ${CYAN}2026                                                    ${BLUE42}  OPR  ${BROWN}║"
				@echo "${BROWN} ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝\n${RESET}"

install:		${BANNERSTAMP}
				@echo "      ${MAGENTA}──╼━━═══${RESET} 💿 Installing ${MAGENTA}${DISP_NAME}${RESET} project ${YELLOW}dependencies${RESET} with ${BRIGHT_BLUE}uv${RESET} 💿 ${MAGENTA}═══━━╾──${RESET}\n"; \
				out=$$(uv sync --dev 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "                                   🔧 %-28b ${GREEN}✅${RESET}\n" "Running ${BRIGHT_BLUE}uv sync --dev${RESET}"; \
					printf "\n    ${MAGENTA}──╼━━═══${RESET} ✅ ${MAGENTA}${DISP_NAME}${RESET} project ${YELLOW}dependencies${RESET} installation  ${GREEN}complete${RESET} ✅ ${MAGENTA}═══━━╾──${RESET}\n\n"; \
					echo "To run ${MAGENTA}${DISP_NAME}${RESET}, type:"; \
					echo "${YELLOW}⌨  ${WHITE_ON_BLUE42} make run ${RESET}${YELLOW}↩${RESET}\n"; \
				else \
					printf "                      ${MAGENTA}──╼━━═══${RESET} 🔧 %-28b ${RED}❌${RESET}\n\n" "Running ${BRIGHT_BLUE}uv sync --dev${RESET} ${MAGENTA}═══━━╾──${RESET}"; \
					printf '%s\n' "$$out"; \
					exit $$status; \
				fi

run:			${BANNERSTAMP}
				@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} project ${CYAN}launched${RESET} 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
				mkdir -p data/output; \
				uv run python -m ${NAME} $(filter-out $@,$(MAKECMDGOALS))
		
debug:			${BANNERSTAMP}
				@echo "                     ${MAGENTA}──╼━━═══${RESET} 🪲 Debugging ${MAGENTA}${DISP_NAME}${RESET} 🪲 ${MAGENTA}═══━━╾──${RESET}\n"
				@mkdir -p data/output
				@uv run python -m pdb ${NAME}.py

lint:			${BANNERSTAMP}
				@echo "            ${MAGENTA}──╼━━═══${RESET} 🔎 Checking ${MAGENTA}${DISP_NAME}${RESET} compliance to ${BRIGHT_BLUE}lint${RESET} 🔍 ${MAGENTA}═══━━╾──${RESET}"; \
				out=$$(uv run flake8 $(FLAKE8_TGT) 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "\n                                      $(BRIGHT_BLUE)flake8$(RESET) . . . $(BRIGHT_GREEN)✓$(RESET)\n"; \
				else \
					printf '%s\n' "$$out"; \
					printf "\n                                      $(BRIGHT_BLUE)flake8$(RESET) . . . $(RED)✗$(RESET)\n"; \
				fi; \
				out=$$(uv run mypy $(MYPY_TGT) \
					--warn-return-any \
					--warn-unused-ignores \
					--ignore-missing-imports \
					--disallow-untyped-defs \
					--check-untyped-defs 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "\n                                      $(BRIGHT_BLUE)mypy$(RESET) . . . . $(BRIGHT_GREEN)✓$(RESET)\n\n"; \
				else \
					printf '%s\n' "$$out"; \
					printf "\n                                      $(BRIGHT_BLUE)mypy$(RESET) . . . . $(RED)✗$(RESET)\n\n"; \
				fi

lint-strict:	${BANNERSTAMP}
				@echo "        ${MAGENTA}──╼━━═══${RESET} 🔎 Checking ${MAGENTA}${DISP_NAME}${RESET} strict compliance to ${BRIGHT_BLUE}lint${RESET} 🔍 ${MAGENTA}═══━━╾──${RESET}"; \
				out=$$(uv run flake8 $(FLAKE8_TGT) 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "\n                                      $(BRIGHT_BLUE)flake8$(RESET) . . . $(BRIGHT_GREEN)✓$(RESET)\n"; \
				else \
					printf '%s\n' "$$out"; \
					printf "\n                                      $(BRIGHT_BLUE)flake8$(RESET) . . . $(RED)✗$(RESET)\n"; \
				fi; \
				out=$$(uv run mypy $(MYPY_TGT) --strict 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "\n                                      $(BRIGHT_BLUE)mypy$(RESET) . . . . $(BRIGHT_GREEN)✓$(RESET)\n\n"; \
				else \
					printf '%s\n' "$$out"; \
					printf "\n                                      $(BRIGHT_BLUE)mypy$(RESET) . . . . $(RED)✗$(RESET)\n\n"; \
				fi

clean:			${BANNERSTAMP}
				@echo "                  ${MAGENTA}──╼━━═══${RESET} 🧹 ${YELLOW}Cleaning${RESET} Python cache folders 🧹 ${MAGENTA}═══━━╾──${RESET}"; \
				count=0; \
				find . -type d -name "__pycache__" -exec rm -rf {} + && count=$$((count + 1)); \
				find . -type d -name ".mypy_cache" -exec rm -rf {} + && count=$$((count + 1)); \
				find . -type d -name ".pytest_cache" -exec rm -rf {} + && count=$$((count + 1)); \
				find . -type d -name ".venv" -exec rm -rf {} + && count=$$((count + 1)); \
				find . -name "*.pyc" -delete; \
				printf "\n             ${MAGENTA}──╼━━═══${RESET} ${GREEN}Cleanup complete${RESET} — cache targets processed: ${CYAN}%d${RESET} ${MAGENTA}═══━━╾──${RESET}\n\n" "$$count"

fclean:			clean
				@echo "             ${MAGENTA}──╼━━═══${RESET} 💥 ${YELLOW}Removing${RESET}  project environment artifacts 💥 ${MAGENTA}═══━━╾──${RESET}"; \
				count=0; \
				rm -rf data/processed/* && count=$$((count + 1)); \
				rm -rf data/vector/* && count=$$((count + 1)); \
				rm -rf data/output/* && count=$$((count + 1)); \
				rm -rf output && count=$$((count + 1)); \
				rm -f data/config.ini && count=$$((count + 1)); \
				rm -f ${BANNERSTAMP}; \
				printf "\n          ${MAGENTA}──╼━━═══${RESET} ✅ ${GREEN}Full cleanup complete ${RESET} — targets processed: ${CYAN}%d${RESET} ✅ ${MAGENTA}═══━━╾──${RESET}\n\n" "$$count"

re:				fclean install

index:					${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}index${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} index
		
index_hybrid:			${BANNERSTAMP}
						@echo "              ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}hybrid index${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} index --hybrid_retrieval True

search:					${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}search${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} search Command
		
search_hybrid:			${BANNERSTAMP}
						@echo "              ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}hybrid search${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} search Command --hybrid_retrieval True

search_dataset:			${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}search_dataset${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} search_dataset --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json --k 10 --save_directory data/output/search_results --use_cache True
		
search_dataset_hybrid:	${BANNERSTAMP}
						@echo "              ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}hybrid search_dataset${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} search_dataset --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json --k 10 --save_directory data/output/search_results --use_cache True --hybrid_retrieval True
		
answer:					${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}answer${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} answer "How to configure OpenAI server?" --k 10
		
answer_hybrid:			${BANNERSTAMP}
						@echo "              ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}hybrid answer${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} answer "How to configure OpenAI server?" --k 10 --hybrid_retrieval True
		
answer_dumb:			${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}answer${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} answer "What is 42?" --k 10
		
answer_nonsense:		${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}answer${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} answer "How to cook fried eggs?" --k 10
		
answer_dataset:			${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}answer${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} answer_dataset --student_search_results_path data/output/search_results/dataset_docs_public.json --save_directory data/output/search_results_and_answer
		
evaluate:				${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}answer${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} evaluate --student_search_results_path data/output/search_results/dataset_docs_public.json --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json --k 10
		
interface:				${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}interface${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run python -m ${NAME} interface
		
start-api: 				${BANNERSTAMP}
						@echo "                 ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} launched in ${CYAN}API${RESET} mode 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
						uv run uvicorn ${FOLDER}command.api:app --reload

%:
	@:

.PHONY: install run debug clean fclean re lint lint-strict
