
import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;

import javax.swing.JFrame;
import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;
import javax.swing.text.BadLocationException;

import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.HashMap;
import java.util.Map;

import ro.sync.ecss.extensions.api.ArgumentDescriptor;
import ro.sync.ecss.extensions.api.ArgumentsMap;
import ro.sync.ecss.extensions.api.AuthorAccess;
import ro.sync.ecss.extensions.api.AuthorConstants;
import ro.sync.ecss.extensions.api.AuthorDocumentController;
import ro.sync.ecss.extensions.api.AuthorOperation;
import ro.sync.ecss.extensions.api.AuthorOperationException;
import ro.sync.ecss.extensions.api.node.AttrValue;
import ro.sync.ecss.extensions.api.node.AuthorElement;
import ro.sync.ecss.extensions.api.node.AuthorNode;

public class QueryLobidGnd implements AuthorOperation {

	public void doOperation(AuthorAccess authorAccess, ArgumentsMap args)
			throws IllegalArgumentException, AuthorOperationException {

		AuthorDocumentController documentController = authorAccess.getDocumentController();

		AuthorElement currentElement = (AuthorElement) documentController.findNodesByXPath(".", false, false, false)[0];
		AuthorElement searchElement = currentElement.getElementsByLocalName("persName")[0];
		String searchString = "";
		try {
			searchString = searchElement.getTextContent();
		} catch (BadLocationException e1) {
			// TODO Auto-generated catch block
			e1.printStackTrace();
		}

		String searchTerm = (String) JOptionPane.showInputDialog(null, "Enter your search term:", "Search Dialog",
				JOptionPane.QUESTION_MESSAGE, null, null, searchString);

		if (searchTerm != null && !searchTerm.trim().isEmpty()) {
			try {

				// get list of possible persons
				String queryBase = "https://lobid.org/gnd/";
				String queryParam = "search?&q=" + searchTerm.replaceAll(" ", "+")
						+ "&size=20&format=json&filter=type:Person%20OR%20type:CorporateBody";

				String finalQuery = queryBase + queryParam;

				HttpClient httpClient = HttpClients.createDefault();
				HttpGet httpGet = new HttpGet(finalQuery);

				String responseBody = EntityUtils.toString(httpClient.execute(httpGet).getEntity());

				JSONObject data = new JSONObject(responseBody);

				JSONArray searchResults = data.getJSONArray("member");

				if (searchResults.length() > 0) {

					Map<String, String> nameToId = new HashMap<String, String>();

					for (int i = 0; i < searchResults.length(); i++) {
						JSONObject result = searchResults.getJSONObject(i);
						String preferredName = result.optString("preferredName");
						String gndNumber = result.optString("gndIdentifier");
						String dateOfBirthDisplay = "";
						if (result.has("dateOfBirth")) {
							JSONArray dobArray = result.getJSONArray("dateOfBirth");
							if (dobArray.length() > 0) {
								dateOfBirthDisplay = ", *" + dobArray.optString(0);
							}
						}

						String displayedLabelDescription = preferredName + " (" + gndNumber + dateOfBirthDisplay + ")";

						nameToId.put(displayedLabelDescription, gndNumber);
					}

					JFrame parentFrame = new JFrame();
					OpenDialog dialog = new OpenDialog(parentFrame, nameToId.keySet().toArray(new String[0]),
							"Search Results", true);

					String selectedLabel = dialog.getSelectedID();

					String selectedId = nameToId.get(selectedLabel);

					JSONObject selectedData = searchResults
							.optJSONObject(getIndexByLobiddataId(searchResults, selectedId));

					String dateOfBirth = "";
					String gender = "";
					String gndLinkId = "";
					String wikiLink = "";
					String occupation = "";
					String academicDegree = "";

					gndLinkId = selectedData.optString("id");

					if (selectedData.has("dateOfBirth")) {
						JSONArray dobArray = selectedData.getJSONArray("dateOfBirth");
						if (dobArray.length() > 0) {
							dateOfBirth = dobArray.optString(0);
						}
					}

					if (selectedData.has("gender")) {
						JSONArray genArray = selectedData.getJSONArray("gender");
						if (genArray.length() > 0) {
							JSONObject genderElement = genArray.optJSONObject(0);
							gender = genderElement.optString("id");
							gender = gender.replaceAll("https://d-nb.info/standards/vocab/gnd/gender#", "");
						}
					} else {
						gender = "CorporateBody";
					}

					if (selectedData.has("wikipedia")) {
						JSONArray wikiArray = selectedData.getJSONArray("wikipedia");
						if (wikiArray.length() > 0) {
							JSONObject wikiElement = wikiArray.optJSONObject(0);
							wikiLink = wikiElement.optString("id");
						}
					}

					if (selectedData.has("professionOrOccupation")) {
						JSONArray occupationArray = selectedData.getJSONArray("professionOrOccupation");
						if (occupationArray.length() > 0) {
							for (int i = 0; i < occupationArray.length(); i++) {
								JSONObject occupationElement = occupationArray.optJSONObject(i);
								occupation = occupation + "<occupation xmlns=\"http://www.tei-c.org/ns/1.0\">"
										+ occupationElement.optString("label") + "</occupation>\n";
							}
						}
					}

					if (selectedData.has("academicDegree")) {
						JSONArray educationArray = selectedData.getJSONArray("academicDegree");
						if (educationArray.length() > 0) {
							for (int i = 0; i < educationArray.length(); i++) {
								academicDegree = academicDegree + "<education xmlns=\"http://www.tei-c.org/ns/1.0\">" + educationArray.optString(i) + "</education>\n";
							}
						}
					}

					//JOptionPane.showMessageDialog(null,
					//		gndLinkId + gender + wikiLink + occupation + dateOfBirth + academicDegree);

					// Insert as nodes
					// gender
					documentController.setAttribute("gender", new AttrValue(gender), currentElement);
					// ref
					documentController.setAttribute("ref", new AttrValue(gndLinkId), currentElement);

					// occupation
					if (!occupation.equals("")) {
						AuthorElement occupationElement = currentElement.getElementsByLocalName("occupation")[0];
						documentController.deleteNode(occupationElement);
						documentController.insertXMLFragment(occupation, (AuthorNode) currentElement,
								AuthorConstants.POSITION_INSIDE_LAST);
					}

					// birth
					if (!dateOfBirth.equals("")) {
						String fragmentBirth = "<birth when=\"" + dateOfBirth
								+ "\" xmlns=\"http://www.tei-c.org/ns/1.0\">" + dateOfBirth.substring(0, 4)
								+ "</birth>";
						AuthorElement birthElement = currentElement.getElementsByLocalName("birth")[0];
						documentController.deleteNode(birthElement);
						documentController.insertXMLFragment(fragmentBirth, (AuthorNode) currentElement,
								AuthorConstants.POSITION_INSIDE_LAST);

					}
					
					// education
					if (!academicDegree.equals("")) {
						AuthorElement educationElement = currentElement.getElementsByLocalName("education")[0];
						documentController.deleteNode(educationElement);
						documentController.insertXMLFragment(academicDegree, (AuthorNode) currentElement,
								AuthorConstants.POSITION_INSIDE_LAST);
					}

					// wiki
					AuthorElement wikiElement = currentElement.getElementsByLocalName("ref")[0];
					documentController.deleteNode(wikiElement);
					String fragmentWiki = "<ref target=\"" + wikiLink + "\" xmlns=\"http://www.tei-c.org/ns/1.0\">"
							+ wikiLink + "</ref>";
					documentController.insertXMLFragment(fragmentWiki, (AuthorNode) currentElement,
							AuthorConstants.POSITION_INSIDE_LAST);

				}
			} catch (Exception e) {
				throw new AuthorOperationException("Failed to retrieve data from Lobid-GND.", e);
			}
		}
	}

	// Method to get the index of a search result based on its Wikidata ID
	private static int getIndexByLobiddataId(JSONArray searchResults, String gndID) {
		for (int i = 0; i < searchResults.length(); i++) {
			JSONObject result = searchResults.getJSONObject(i);
			if (result.optString("gndIdentifier").equals(gndID)) {
				return i;
			}
		}
		return -1; // ID not found
	}

	public String getDescription() {
		// TODO Auto-generated method stub
		return null;
	}

	public ArgumentDescriptor[] getArguments() {
		return null;
	}

}
