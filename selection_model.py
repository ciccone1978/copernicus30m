from PySide6.QtCore import QObject, Signal

class SelectionModel(QObject):
    """
    Manages the application's data state, specifically the set of selected tiles.
    Emits a signal whenever the selection changes.
    This class is completely independent of the UI.
    """
    # Signal that will be emitted with the new, complete set of selected tiles whenever a change occurs.
    selection_changed = Signal(set)

    def __init__(self):
        super().__init__()
        # Use a private variable to store the state.
        # A set is used because it's efficient for adding, removing, and
        # checking for existence, and it automatically handles duplicates.
        self._selected_tiles = set()

    def toggle_selection(self, tile):
        """
        The primary method for modifying the selection.
        It adds a tile to the selection if it's not already present,
        or removes it if it is.

        After modifying the set, it emits the 'selection_changed' signal
        to notify any listeners that the state has been updated.

        Args:
            tile (tuple): A tuple of (integer_latitude, integer_longitude)
                          representing the tile.
        """
        if tile in self._selected_tiles:
            self._selected_tiles.remove(tile)
        else:
            self._selected_tiles.add(tile)
        
        # Announce to the application that the selection has changed.
        # We emit a copy of the set to ensure the original cannot be
        # modified from outside this class.
        self.selection_changed.emit(self._selected_tiles.copy())

    def get_selected_tiles(self):
        """
        A simple getter method to allow other parts of the application
        (like the controller) to query the current state.

        Returns:
            set: A copy of the set of currently selected tiles.
        """
        return self._selected_tiles.copy()

    def has_selection(self):
        """
        A convenience method to check if the selection is empty or not.

        Returns:
            bool: True if at least one tile is selected, False otherwise.
        """
        return len(self._selected_tiles) > 0
    
    def set_selection(self, tiles: set):
        """
        Replaces the current selection with a new set of tiles.

        Args:
            tiles (set): The new set of (lat, lon) tuples for the selection.
        """
        if self._selected_tiles != tiles:
            self._selected_tiles = tiles
            self.selection_changed.emit(self._selected_tiles.copy())

    def clear_selection(self):
        """Resets the selection to an empty set."""
        self._selected_tiles.clear()
        self.selection_changed.emit(self._selected_tiles.copy())