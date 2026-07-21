import functools

import FreeCAD as App
import FreeCADGui as Gui


def with_undo(transaction_name="Macro Operation"):
    """
    A decorator that wraps a function in a FreeCAD undo transaction.
    If the function succeeds, it commits. If it crashes, it aborts.
    """

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            doc = App.ActiveDocument
            if not doc:
                App.Console.PrintError(
                    "Error: No active document for undo transaction.\n")
                return func(*args, **kwargs)

            # 1. Start recording
            doc.openTransaction(transaction_name)

            try:
                # Run the actual macro logic
                result = func(*args, **kwargs)

                # 2. Save the recording
                doc.commitTransaction()
                return result

            except Exception as e:
                # 3. Wipe the recording if something broke
                doc.abortTransaction()
                App.Console.PrintError(
                    f"Undo Transaction Aborted. '{transaction_name}' failed: {e}\n"
                )

        return wrapper

    return decorator


def get_active_body(base_obj=None):
    """Finds the active PartDesign Body, falling back to the base object's parent."""
    active_body = None
    if Gui.ActiveDocument:
        active_body = Gui.ActiveDocument.ActiveView.getActiveObject("pdbody")

    if not active_body and base_obj:
        for parent in base_obj.InList:
            if parent.isDerivedFrom("PartDesign::Body"):
                active_body = parent
                break

    if not active_body:
        App.Console.PrintWarning(
            "Warning: No Active Body found. Placing objects in root.\n")

    return active_body


def build_additive_loft(active_body, loft_label, profile, sections, hide_list):
    """Generates an Additive Loft inside the active body and hides intermediate sketches."""
    if not active_body or not sections:
        App.Console.PrintWarning(
            "Skipped Additive Loft: No Active Body or insufficient sections.\n")
        return None

    try:
        loft = active_body.newObject("PartDesign::AdditiveLoft", loft_label)
        loft.Profile = profile
        loft.Sections = sections

        # Clean up the viewport
        if Gui.ActiveDocument:
            for obj in hide_list:
                doc_obj = Gui.ActiveDocument.getObject(obj.Name)
                if doc_obj:
                    doc_obj.Visibility = False
        return loft

    except Exception as e:
        App.Console.PrintError(f"Error generating Additive Loft: {e}\n")
        return None
