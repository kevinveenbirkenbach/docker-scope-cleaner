.PHONY: test install

# Run the unittest suite
test:
	@echo "Running unittests..."
	python3 -m unittest discover -s . -p "test*.py" -v

# Installation is handled via pkgmgr, so only a hint is printed
install:
	@echo "⚠️  Installation is handled via pkgmgr."
	@echo "   Please run:"
	@echo "       pkgmgr install doscol"
