Mahabhunakasha Scraper - Feature Walkthrough
The application has been successfully enhanced with all requested features. This walkthrough covers the key functionalities and improvements made during this session.

1. Automated Location Selection
The app now automatically selects the default location for testing/demo purposes:

Category: Rural
District: Pune (25)
Taluka: Ambegaon (02)
Village: Sakore (272500020303690000)
Gat Number: Defaults to 1
2. Integrated Map Reports
Official government reports are now accessible directly via proxied links. These include:

Form 7/12
Map Report (Nakasha) These links use the local /api/report proxy to bypass cookie/session restrictions on the government server.
3. High-Precision Map Tools
The map visualization has been upgraded with precise surveyor tools:

UTM Projections: Switch between UTM Zone 43N (West Maharashtra) and 44N (East Maharashtra) for accurate measurements.
Manual Calibration: Fine-tune plot alignment with nudge buttons (+/- 1m, +/- 10m).
Coordinate Popups: Click any point on the plot boundary to see its exact Latitude/Longitude and copy it to your clipboard.
4. Village View (Configurable Progressive Loading)
The "Show All Plots" feature now allows you to see the entire village boundary map with full control over the loading process:

Configurable Plot Limit: A new input field in the map toolbar lets you specify exactly how many plots to load (defaults to 50).
Progressive Rendering: Plots are fetched and drawn 1-by-1 in real-time.
Live Counter: The toolbar button displays the loading progress relative to your limit (e.g., 25/50).
Interactive Boundaries: Click any village plot to see its Gat number.
Visual Distinction: The currently searched plot stays highlighted in blue, while village plots appear as dark gray lines.
5. Multi-Plot Selection (Custom Picks)
You can now hand-pick specific Gat numbers and see them together on the map:

"Add" Button: A new green + button next to the Gat search allows you to add the currently selected Gat No to a "Selected Plots" list.
"Add All" Button: A new blue Add All button quickly adds all survey numbers in the current list to your selection and instantly starts plotting them.
Selection Sidebar: A new list appears in the sidebar displaying all your picked Gat numbers. You can remove individual plots highlighting their tags.
"Plot Selected": Render all your hand-picked plots at once. This now works directly after selecting a village, without requiring a separate single-plot search first. They are drawn in a thin, sharp red color for maximum contrast against satellite imagery.
Combined Zoom: The map automatically zooms to comfortably fit all your selected plots.
Feature Status Summary
Feature	Description	Status
Location Auto-Selection	Pune -> Ambegaon -> Sakore -> Gat 1	✅ Active
Official Map Reports	Proxied links for direct access	✅ Active
Manual Calibration	Nudge buttons for fine-tuning	✅ Active
UTM Projections	Zone 43N & 44N support	✅ Active
Progressive Loading	Real-time village plot drawing	✅ Active
Custom Styling	Thin Red/Blue lines for contrast	✅ Active
Copy Coordinates	One-click copy for boundary points	✅ Active
No Local Cache	Fresh data on every load	✅ Active
Map Download	Official download (Option 1)	❌ Removed/Excluded
