import os
import subprocess
import json
import sys
from mistralai import Mistral

# --- Global variables to store file paths and content ---
main_file_path = None
main_file_content = None
test_file_path = None
test_file_content = None  # Keep track of test file content for correction

# --- API Key Configuration ---
api_key = os.environ.get("MISTRAL_API_KEY")
if not api_key:
    print("❌ Erreur : La variable d'environnement MISTRAL_API_KEY n'est pas définie.")
    exit(1)

# --- Model Configuration ---
# model = "mistral-small-latest"
# model = "codestral-latest"
model = "mistral-medium-latest"


# model = "mistral-large-latest"

# --- File Operations ---
def writeFile(path, content):
    """
    Writes content to a specified file path, creating directories if necessary.
    """
    try:
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Fichier écrit : {path}")
    except IOError as e:
        print(f"❌ Erreur lors de l'écriture du fichier {path}: {e}")


# NEW: Wrapper for writing test files
def writeTestFile(path, content):
    """
    Writes content to a specified test file path and updates global state.
    """
    global test_file_path, test_file_content
    writeFile(path, content)
    test_file_path = path
    test_file_content = content
    print(f"✅ Fichier de test écrit : {path}")


def launchPythonFile(path, is_test_file=False):
    """
    Launches a Python file and captures its output.
    Returns a dictionary with execution details, including test status if it's a test file.
    """
    full_path = os.path.join(os.getcwd(), path)
    test_status = "unknown"
    output = ""
    error_output = ""
    success = False

    try:
        result = subprocess.run(["python", full_path], check=True, capture_output=True, text=True, encoding='utf-8')
        print(f"✅ Fichier Python exécuté : {path}")
        print("--- Début de la sortie du script ---")
        print(result.stdout)
        print("--- Fin de la sortie du script ---")
        output = result.stdout
        success = True

        if is_test_file:
            # Check for common unittest failure indicators
            if "FAIL" in result.stdout or "Error" in result.stdout or "FAILED" in result.stdout:
                test_status = "failed"
            else:
                test_status = "passed"

    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'exécution du fichier Python {path}: {e}")
        print(f"Sortie standard : {e.stdout}")
        print(f"Erreur standard : {e.stderr}")
        output = e.stdout
        error_output = e.stderr or str(e)
        success = False

        if is_test_file:
            test_status = "failed"  # If the test runner itself crashes, it's a test failure.

    file_content_read = ""
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            file_content_read = f.read()
    except Exception as read_err:
        print(f"⚠️ Erreur lors de la lecture du fichier {full_path}: {read_err}")
        file_content_read = "Contenu non disponible."

    return {
        "success": success,
        "output": output,
        "error_output": error_output,
        "test_status": test_status if is_test_file else None,
        "file_content": file_content_read,  # Include file content for correction prompts
        "file_path": path,  # Include file path for correction prompts
        "is_test_file": is_test_file
    }


# NEW: Wrapper for launching test files
def launchTestFile(path):
    """
    Launches a Python test file and returns its execution result.
    """
    print(f"🚀 Lancement du fichier de test : {path}")
    return launchPythonFile(path, is_test_file=True)


# --- Prompt Building Functions ---
# These functions now instruct the LLM to use the new specific functions.

def buildCorrectionPrompt(file_path_to_correct, file_content_to_correct, error_output, context_info=""):
    """
    Builds a prompt for the LLM to correct a Python file based on an error or test failure.
    The LLM should use writeFile (for main) or writeTestFile (for test) and then suggest launchTestFile.
    """
    is_test_file_correction = (file_path_to_correct == test_file_path)
    write_func_name = "writeTestFile" if is_test_file_correction else "writeFile"
    description_action = f"Relancer les tests ({test_file_path})" if test_file_path else "Relancer l'exécution principale"

    return f"""
Tu as accès aux fonctions Python suivantes :
1. writeFile(path: str, content: str) - Pour écrire le fichier principal.
2. writeTestFile(path: str, content: str) - Pour écrire le fichier de test.
3. launchPythonFile(path: str) - Pour exécuter le fichier principal.
4. launchTestFile(path: str) - Pour exécuter le fichier de test.

Tu dois TOUJOURS répondre avec un JSON **valide** et bien échappé :
- Chaînes entourées de doubles guillemets.
- Échappement des caractères spéciaux.
- Ne pas mettre de backslash dans le nom de fichier.

Le champ 'feedback' doit contenir :
- 'action': ex. "launchTestFile path=xxx.py" ou "launchPythonFile path=yyy.py" ou vide.
- 'description': explication de l'action et prochaine étape.

--- Contenu du fichier ({file_path_to_correct}) ---
{file_content_to_correct}

--- Message d'erreur / Contexte ---
{error_output}
{context_info}

Corrige le fichier ci-dessus. Après correction, tu dois suggérer la prochaine action.
Si tu as corrigé le fichier de test, la prochaine action est de relancer les tests.
Si tu as corrigé le fichier principal (suite à un échec de test ou d'exécution), la prochaine action est de relancer les tests.

Exemple de réponse pour la correction :
{{
  "function": "{write_func_name}",
  "arguments": {{
    "path": "{file_path_to_correct}",
    "content": "nouveau contenu corrigé ici"
  }},
  "feedback": {{
    "action": "launchTestFile path={test_file_path if test_file_path else 'chemin_test.py'}",
    "description": "Le fichier a été corrigé. On peut maintenant {description_action}."
  }}
}}
"""


def buildUnitTestPrompt(file_to_test_path: str, file_content: str):
    """
    Builds a prompt for the LLM to create a unit test file for a given Python file.
    The LLM should use writeTestFile and then suggest launchTestFile.
    """
    return f"""
Tu as accès aux fonctions Python suivantes :
1. writeFile(path: str, content: str) - Pour écrire le fichier principal.
2. writeTestFile(path: str, content: str) - Pour écrire le fichier de test.
3. launchPythonFile(path: str) - Pour exécuter le fichier principal.
4. launchTestFile(path: str) - Pour exécuter le fichier de test.

Tu dois TOUJOURS répondre avec un JSON **valide** et bien échappé :
- Chaînes entourées de doubles guillemets.
- Échappement des caractères spéciaux.
- Ne pas mettre de backslash dans le nom de fichier.

Le champ 'feedback' doit contenir :
- 'action': ex. "launchTestFile path=xxx.py" ou vide.
- 'description': explication de l'action et prochaine étape.

--- Contenu du fichier à tester ({file_to_test_path}) ---
{file_content}

Crée un fichier de test unitaire pour le fichier ci-dessus. Le fichier de test doit utiliser le module `unittest` de Python.
Assure-toi que le fichier de test importe correctement les fonctions ou classes du fichier à tester.
Après avoir écrit le fichier de test, tu dois demander son exécution en utilisant `launchTestFile`.

Exemple de réponse pour la création et l'exécution d'un fichier de test :
{{
  "function": "writeTestFile",
  "arguments": {{
    "path": "test_mon_script.py",
    "content": "import unittest\\nfrom mon_script import ma_fonction\\n\\nclass TestMaFonction(unittest.TestCase):\\n    def test_simple(self):\\n        self.assertEqual(ma_fonction(2), 4)\\n\\nif __name__ == '__main__':\\n    unittest.main()"
  }},
  "feedback": {{
    "action": "launchTestFile path=test_mon_script.py",
    "description": "Le fichier de test a été créé. On peut maintenant l'exécuter pour vérifier le code principal."
  }}
}}
"""


def buildInitialPrompt(user_message: str):
    """
    Builds the initial prompt for the LLM based on the user's request.
    The LLM should decide if it wants to create tests or just run the main file.
    """
    escaped = user_message.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f"""
Tu as accès aux fonctions Python suivantes :
1. writeFile(path: str, content: str) - Pour écrire le fichier principal.
2. writeTestFile(path: str, content: str) - Pour écrire le fichier de test.
3. launchPythonFile(path: str) - Pour exécuter le fichier principal.
4. launchTestFile(path: str) - Pour exécuter le fichier de test.

Tu dois TOUJOURS répondre avec un JSON **valide** et bien échappé.

Demande :
"{escaped}"

Tu dois créer un fichier Python principal. Après l'avoir créé, tu dois indiquer dans le champ 'feedback.description'
si tu souhaites créer et exécuter des tests unitaires pour ce fichier ("Maintenant, crée le fichier de test."),
ou si tu souhaites l'exécuter directement ("Exécute le fichier principal directement.").

Exemple 1 (avec tests) :
{{
  "function": "writeFile",
  "arguments": {{
    "path": "sudoku_game.py",
    "content": "import tkinter as tk\\nclass SudokuGame(tk.Tk):\\n    def __init__(self):\\n        super().__init__()\\n        self.title(\\"Sudoku Game\\")\\nif __name__ == \\"__main__\\":\\n    SudokuGame().mainloop()"
  }},
  "feedback": {{
    "action": "",
    "description": "Le fichier principal a été créé. Maintenant, crée le fichier de test."
  }}
}}

Exemple 2 (sans tests, exécution directe) :
{{
  "function": "writeFile",
  "arguments": {{
    "path": "hello_world.py",
    "content": "print(\\"Hello, World!\\")"
  }},
  "feedback": {{
    "action": "",
    "description": "Le fichier principal a été créé. Exécute le fichier principal directement."
  }}
}}
"""


# --- LLM Interaction ---
def generateText(prompt: str) -> str:
    """
    Calls the Mistral API to generate text based on the given prompt.
    """
    try:
        client = Mistral(api_key=api_key)
        chat_response = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return chat_response.choices[0].message.content
    except Exception as e:
        print(f"❌ Erreur appel API Mistral : {e}")
        # Return a valid JSON to prevent breaking the loop
        return json.dumps({
            "function": "none",
            "arguments": {},
            "feedback": {
                "action": "",
                "description": f"Erreur API: {e}"
            }
        })


# --- Function Call Processing ---
def processFunctionCall(llm_response: str, current_phase: str):
    """
    Processes the LLM's JSON response, performs the requested action (writeFile/launchPythonFile/writeTestFile/launchTestFile),
    and determines the next phase of the workflow.
    """
    global main_file_path, main_file_content, test_file_path, test_file_content
    cleaned = llm_response.strip()

    if cleaned.startswith("'''json"):
        cleaned = cleaned[len("'''json"):].strip()
    if cleaned.endswith("'''"):
        cleaned = cleaned[:-len("'''")].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("❌ Erreur JSON :", e)
        print("Contenu reçu :", cleaned)
        raise

    func = data.get("function")
    args = data.get("arguments", {})
    feedback_from_llm = data.get("feedback", {})  # This feedback from LLM is mainly descriptive.

    # Initialize return values
    next_phase = current_phase  # Default: stay in current phase or transition based on action
    action_for_main_loop = ""
    description_for_main_loop = feedback_from_llm.get("description", "")
    error_output_for_main_loop = ""
    test_output_for_main_loop = ""

    if func == "writeFile":
        path = args.get("path")
        content = args.get("content")
        if path and isinstance(content, str):
            writeFile(path, content)
            main_file_path = path
            main_file_content = content
            description_for_main_loop = feedback_from_llm.get("description", f"Fichier principal '{path}' écrit.")
            action_for_main_loop = feedback_from_llm.get("action", "")

            # Specific logic for initial main file write to determine workflow intent
            if current_phase == "INITIAL_PROMPT" or current_phase == "WAITING_FOR_MAIN_FILE_WRITE":
                if "crée le fichier de test" in description_for_main_loop:
                    next_phase = "PROMPT_TEST_CREATION"
                elif "exécute le fichier principal directement" in description_for_main_loop:
                    next_phase = "WAITING_FOR_MAIN_FILE_RUN_ACTION"
                else:
                    # Fallback if LLM's description isn't clear, assume test creation
                    print("⚠️ Description LLM ambigüe pour le workflow initial. Par défaut: création de test.")
                    next_phase = "PROMPT_TEST_CREATION"
            # If writeFile is called during correction, the next_phase is determined by the correction logic
            # which leads back to running tests.
            elif current_phase in ["TESTS_FAILED_CORRECTING_MAIN", "MAIN_FILE_FAILED_CORRECTING"]:
                next_phase = "RUNNING_TESTS"  # After main file correction, always re-run tests
                action_for_main_loop = f"launchTestFile path={test_file_path}" if test_file_path else ""
                description_for_main_loop += " (Relance des tests suggérée suite à correction du fichier principal)."
            else:
                print(f"⚠️ writeFile: phase inconnue {current_phase}. Ne peut pas déterminer la prochaine phase.")
                next_phase = "FINISHED"  # Fallback
        else:
            print("⚠️ writeFile: arguments invalides.")
            next_phase = "FINISHED"  # Error state
    elif func == "writeTestFile":  # NEW
        path = args.get("path")
        content = args.get("content")
        if path and isinstance(content, str):
            writeTestFile(path, content)
            description_for_main_loop = feedback_from_llm.get("description", f"Fichier de test '{path}' écrit.")
            action_for_main_loop = feedback_from_llm.get("action", "")
            # After writing test file, the next step is always to run tests
            next_phase = "RUNNING_TESTS"
            if not action_for_main_loop and test_file_path:  # Ensure action is set if LLM didn't
                action_for_main_loop = f"launchTestFile path={test_file_path}"
        else:
            print("⚠️ writeTestFile: arguments invalides.")
            next_phase = "FINISHED"  # Error state
    elif func == "launchPythonFile":  # Used by LLM to launch main file
        path = args.get("path")
        if path:
            action_for_main_loop = f"launchPythonFile path={path}"
            description_for_main_loop = feedback_from_llm.get("description",
                                                              f"Action de lancement du fichier principal '{path}' reçue.")
            next_phase = "RUNNING_MAIN_FILE"  # Explicitly set next phase for direct execution
        else:
            print("⚠️ launchPythonFile: chemin de fichier manquant.")
            next_phase = "FINISHED"  # Error state
    elif func == "launchTestFile":  # Used by LLM to launch test file
        path = args.get("path")
        if path:
            action_for_main_loop = f"launchTestFile path={path}"
            description_for_main_loop = feedback_from_llm.get("description",
                                                              f"Action de lancement du fichier de test '{path}' reçue.")
            next_phase = "RUNNING_TESTS"  # Explicitly set next phase for test execution
        else:
            print("⚠️ launchTestFile: chemin de fichier manquant.")
            next_phase = "FINISHED"  # Error state
    else:
        print(f"⚠️ Fonction inconnue : {func}")
        next_phase = "FINISHED"  # Unknown function, stop.

    return {
        "action": action_for_main_loop,
        "description": description_for_main_loop,
        "next_phase": next_phase,  # This is the phase for the *next* iteration's prompt generation
        "error_output": error_output_for_main_loop,
        "test_output": test_output_for_main_loop
    }


# === Entry Point ===

if len(sys.argv) < 2:
    print("Usage: python main.py \"Votre message\"")
    exit(1)

user_message = sys.argv[1]
# Initial phase: Ask LLM to create the main file and decide workflow
current_phase = "INITIAL_PROMPT"
# feedback_from_action will hold results from launchPythonFile/launchTestFile or LLM's feedback after processFunctionCall
feedback_from_action = {"description": "Début du traitement.", "action": "", "error_output": "", "test_output": ""}
MAX_LOOPS = 15  # Increased max loops for the more complex workflow
loop_count = 0
stop_loop = False

print(f"Démarrage (max {MAX_LOOPS} itérations)...")

while not stop_loop and loop_count < MAX_LOOPS:
    loop_count += 1
    print(f"\n--- Itération {loop_count} ---")
    print(f"Phase actuelle : {current_phase}")
    print(f"État : {feedback_from_action['description']}")

    prompt = ""
    llm_response = ""

    # Logic to determine the prompt based on the current phase
    if current_phase == "INITIAL_PROMPT":
        prompt = buildInitialPrompt(user_message)
        # After building initial prompt, we wait for LLM's response to determine next phase
        # current_phase will be updated by processFunctionCall
    elif current_phase == "PROMPT_TEST_CREATION":
        if not main_file_path or not main_file_content:
            print("❌ Erreur: Chemin ou contenu du fichier principal manquant pour écrire le fichier de test.")
            stop_loop = True
            break
        prompt = buildUnitTestPrompt(main_file_path, main_file_content)
    elif current_phase == "RUNNING_TESTS":
        if feedback_from_action.get("action", "").startswith("launchTestFile"):
            file_to_launch = feedback_from_action["action"].split("path=")[1].strip()
            result_of_launch = launchTestFile(file_to_launch)  # Use the new launchTestFile

            if result_of_launch["test_status"] == "passed":
                current_phase = "TESTS_PASSED_PROMPT_MAIN_RUN"
                feedback_from_action[
                    "description"] = f"Tests réussis pour {file_to_launch}. Demande de lancement du fichier principal."
                feedback_from_action["action"] = ""  # Clear action, next step is prompt
            elif result_of_launch["error_output"]:  # Test file itself had an error (e.g., syntax)
                current_phase = "TEST_FILE_FAILED_CORRECTING"
                feedback_from_action[
                    "description"] = f"Erreur lors de l'exécution du fichier de test '{file_to_launch}'. Correction requise."
                feedback_from_action["error_output"] = result_of_launch["error_output"]
                feedback_from_action["output"] = result_of_launch["output"]  # Store stdout for context
                # test_file_content and test_file_path are already global, no need to pass via feedback_from_action
                feedback_from_action["action"] = ""  # Clear action, next step is prompt
            else:  # Tests failed due to main code logic (no error_output, but test_status is failed)
                current_phase = "TESTS_FAILED_CORRECTING_MAIN"
                feedback_from_action[
                    "description"] = f"Tests échoués pour {file_to_launch}. Correction du fichier principal requise."
                feedback_from_action["error_output"] = result_of_launch["error_output"]  # This might be empty
                feedback_from_action["test_output"] = result_of_launch["output"]
                feedback_from_action["action"] = ""  # Clear action, next step is prompt
            continue  # Skip LLM call in this iteration as we just executed a file
        else:
            print(
                "❌ Erreur: Action inattendue pour RUNNING_TESTS. Aucune action de lancement de fichier de test trouvée.")
            stop_loop = True
            break
    elif current_phase == "TESTS_PASSED_PROMPT_MAIN_RUN":
        # After tests pass, prompt LLM to launch the main file
        prompt = f"""
Tu as accès aux fonctions Python suivantes :
1. writeFile(path: str, content: str) - Pour écrire le fichier principal.
2. writeTestFile(path: str, content: str) - Pour écrire le fichier de test.
3. launchPythonFile(path: str) - Pour exécuter le fichier principal.
4. launchTestFile(path: str) - Pour exécuter le fichier de test.

Tu dois TOUJOURS répondre avec un JSON **valide** et bien échappé.

Le champ 'feedback' doit contenir :
- 'action': ex. "launchPythonFile path=xxx.py" ou vide.
- 'description': explication de l'action et prochaine étape.

Les tests unitaires pour le fichier principal ({main_file_path}) ont réussi.
Maintenant, exécute le fichier principal.

Exemple :
{{
  "function": "launchPythonFile",
  "arguments": {{
    "path": "{main_file_path}"
  }},
  "feedback": {{
    "action": "launchPythonFile path={main_file_path}",
    "description": "Les tests ont réussi. Lancement du fichier principal."
  }}
}}
"""
        # current_phase will be updated by processFunctionCall based on LLM's response
    elif current_phase == "TESTS_FAILED_CORRECTING_MAIN":
        if not main_file_path or not main_file_content:
            print("❌ Erreur: Chemin ou contenu du fichier principal manquant pour la correction.")
            stop_loop = True
            break
        context = f"Sortie du test :\n{feedback_from_action.get('test_output', 'N/A')}"
        prompt = buildCorrectionPrompt(main_file_path, main_file_content, feedback_from_action["error_output"], context)
        # current_phase will be updated by processFunctionCall after LLM writes main file
    elif current_phase == "TEST_FILE_FAILED_CORRECTING":
        if not test_file_path or not test_file_content:  # Use global test_file_path/content
            print("❌ Erreur: Informations manquantes pour la correction du fichier de test.")
            stop_loop = True
            break
        context = f"Sortie du test (erreur) :\n{feedback_from_action.get('output', 'N/A')}"
        prompt = buildCorrectionPrompt(
            test_file_path,  # Use global test_file_path
            test_file_content,  # Use global test_file_content
            feedback_from_action["error_output"],
            context
        )
        # current_phase will be updated by processFunctionCall after LLM writes test file
    elif current_phase == "RUNNING_MAIN_FILE":
        if feedback_from_action.get("action", "").startswith("launchPythonFile"):
            file_to_launch = feedback_from_action["action"].split("path=")[1].strip()
            result_of_launch = launchPythonFile(file_to_launch)  # is_test_file=False by default

            if result_of_launch["success"]:
                current_phase = "FINISHED"
                feedback_from_action["description"] = f"Fichier principal '{file_to_launch}' exécuté avec succès."
                stop_loop = True
            else:  # Main file execution failed
                current_phase = "MAIN_FILE_FAILED_CORRECTING"
                feedback_from_action[
                    "description"] = f"Échec de l'exécution du fichier principal '{file_to_launch}'. Correction requise."
                feedback_from_action["error_output"] = result_of_launch["error_output"]
                feedback_from_action["output"] = result_of_launch["output"]  # Store stdout for context
                feedback_from_action["action"] = ""  # Clear action, next step is prompt
            continue  # Skip LLM call in this iteration as we just executed a file
        else:
            print("❌ Erreur: Action inattendue pour RUNNING_MAIN_FILE. Aucune action de lancement de fichier trouvée.")
            stop_loop = True
            break
    elif current_phase == "MAIN_FILE_FAILED_CORRECTING":
        if not main_file_path or not main_file_content or not feedback_from_action.get("error_output"):
            print(
                "❌ Erreur: Informations manquantes pour la correction du fichier principal suite à un échec d'exécution.")
            stop_loop = True
            break
        context = f"Sortie standard du fichier principal :\n{feedback_from_action.get('output', 'N/A')}"
        prompt = buildCorrectionPrompt(main_file_path, main_file_content, feedback_from_action["error_output"], context)
        # current_phase will be updated by processFunctionCall after LLM writes main file
    elif current_phase == "FINISHED":
        stop_loop = True
        break
    # Phases that don't generate a prompt but wait for an action from LLM's previous response
    elif current_phase in ["WAITING_FOR_MAIN_FILE_WRITE", "WAITING_FOR_TEST_FILE_WRITE",
                           "WAITING_FOR_MAIN_FILE_RUN_ACTION"]:
        # These phases rely on the 'action' set by processFunctionCall in the previous iteration
        pass  # No prompt generation, just proceed to processFunctionCall
    else:
        print(f"❌ Phase inconnue : {current_phase}")
        stop_loop = True
        break

    if prompt:  # Only call LLM if a prompt was generated
        # Affiche le prompt qui sera envoyé au modèle LLM.
        # Ce prompt contient toutes les informations nécessaires au modèle pour comprendre la tâche
        # (créer un fichier, corriger un fichier, créer un test, etc.) et le contexte actuel
        # (contenu du fichier, messages d'erreur, résultats de tests).
        print("📤 Prompt LLM :", prompt)
        llm_response = generateText(prompt)
        # Affiche la réponse JSON brute reçue du modèle LLM.
        # Cette réponse contient la fonction que le modèle souhaite appeler (writeFile ou launchPythonFile)
        # ainsi que les arguments nécessaires pour cette fonction et un feedback descriptif.
        print("🧠 Réponse LLM :", llm_response)

        try:
            # processFunctionCall now returns the next_phase and updated feedback_from_action
            processed_result = processFunctionCall(llm_response, current_phase)
            current_phase = processed_result["next_phase"]  # This is the crucial update for the next iteration's prompt
            feedback_from_action["description"] = processed_result["description"]
            feedback_from_action["action"] = processed_result.get("action",
                                                                  "")  # May contain launchPythonFile/launchTestFile action
            feedback_from_action["error_output"] = processed_result.get("error_output", "")
            feedback_from_action["test_output"] = processed_result.get("test_output", "")

        except Exception as e:
            print(f"❌ Erreur dans le traitement : {e}")
            feedback_from_action = {"action": "", "description": "Erreur de traitement", "error_output": str(e)}
            current_phase = "FINISHED"
            stop_loop = True
    else:
        # If no prompt was generated, it means the current_phase (e.g., RUNNING_TESTS or RUNNING_MAIN_FILE)
        # already handled the action and updated the current_phase. So, we just continue the loop.
        pass

if loop_count >= MAX_LOOPS:
    print("⚠️ Limite de boucle atteinte.")
else:
    print("✅ Processus terminé.")
