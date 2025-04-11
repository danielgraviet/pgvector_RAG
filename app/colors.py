# colors.py

from colorama import Fore, Style, init

# Initialize colorama. autoreset=True automatically adds Style.RESET_ALL
# to the end of each print statement, so colors don't bleed into the next line.
init(autoreset=True)

# Define color constants
ANSWER = Fore.GREEN + Style.BRIGHT  # Bright Green for the final answer
HEADING = Fore.CYAN + Style.BRIGHT   # Bright Cyan for headings like "Thought process:"
THOUGHT = Fore.YELLOW                # Yellow for individual thoughts
CONTEXT_LABEL = Fore.MAGENTA         # Magenta for the "Context:" label
CONTEXT_TRUE = Fore.GREEN            # Green for True context
CONTEXT_FALSE = Fore.RED             # Red for False context
QUERY = Fore.BLUE + Style.BRIGHT     # Bright Blue for the initial query text
SEPARATOR = Fore.WHITE + Style.DIM   # Dim white for separators

# You can add more colors as needed
# Example: ERROR = Fore.RED + Style.BRIGHT