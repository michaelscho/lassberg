import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;

import javax.swing.JFrame;
import javax.swing.JOptionPane;
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

public class QueryWikidata implements AuthorOperation {

	public void doOperation(AuthorAccess authorAccess, ArgumentsMap args)
			throws IllegalArgumentException, AuthorOperationException {
		
		AuthorDocumentController documentController = authorAccess.getDocumentController();

		AuthorElement currentElement = (AuthorElement) documentController.findNodesByXPath(".", false, false, false)[0];
		AuthorElement searchElement = currentElement.getElementsByLocalName("placeName")[0];
		AuthorElement locationElement = currentElement.getElementsByLocalName("location")[0];
		AuthorElement geoElement = locationElement.getElementsByLocalName("geo")[0];
		
		
		String searchTerm = null;
		try {
			searchTerm = searchElement.getTextContent();
		} catch (BadLocationException e1) {
			// TODO Auto-generated catch block
			e1.printStackTrace();
		}
		

		try {
			String encodedSearchTerm = URLEncoder.encode(searchTerm, "UTF-8");

			String apiUrl = "https://www.wikidata.org/w/api.php" + "?action=wbsearchentities" + "&format=json"
					+ "&language=de" + "&search=" + encodedSearchTerm + "&uselang=de" + "&fuzzy=1" + "&limit=10";

			HttpClient httpClient = HttpClients.createDefault();
			HttpGet httpGet = new HttpGet(apiUrl);

			String responseBody = EntityUtils.toString(httpClient.execute(httpGet).getEntity());

			JSONObject data = new JSONObject(responseBody);
			JSONArray searchResults = data.getJSONArray("search");

			if (searchResults.length() > 0) {

				Map<String, String> labelToId = new HashMap<String, String>();

				for (int i = 0; i < searchResults.length(); i++) {
					JSONObject result = searchResults.getJSONObject(i);
					String label = result.optString("label");
					String description = result.optString("description");
					String displayedLabelDescription = label + " (" + description + ")";
					String id = result.optString("id"); // Get the Wikidata ID
					labelToId.put(displayedLabelDescription, id);
				}

				// Assuming you have a JFrame as your parent frame
				JFrame parentFrame = new JFrame();
				OpenDialog dialog = new OpenDialog(parentFrame, labelToId.keySet().toArray(new String[0]),
						"Search Results", true);

				String selectedLabel = dialog.getSelectedID(); // Get the selected label
				String selectedId = labelToId.get(selectedLabel); // Get the corresponding Wikidata ID

				JSONObject selectedData = searchResults.optJSONObject(getIndexByWikidataId(searchResults, selectedId));
			
				String wikilink = selectedData.optString("url");
	            String labelDe = selectedData.optString("label");
	            String description = selectedData.optString("description");
	            String wikiId = selectedData.optString("id");

	            String coordinates = fetchCoordinates(wikiId);
	            
	            if (coordinates.equals(null)) {
		            JOptionPane.showMessageDialog(null, "Koordinaten konnten nicht abgerufen werden.");

	            } else {            
	            
	    		documentController.setAttribute("ref", new AttrValue("https:" + wikilink), searchElement);
	    		
	    		String fragmentDescription = "<desc type=\"wikidata\" xmlns=\"http://www.tei-c.org/ns/1.0\">" + description + "</desc>";
	    		documentController.insertXMLFragment(fragmentDescription, (AuthorNode) currentElement, AuthorConstants.POSITION_INSIDE_LAST);

	            
	            documentController.deleteNode(geoElement);
	            String fragmentCoords = "<geo ana=\"wgs84\" xmlns=\"http://www.tei-c.org/ns/1.0\">" + coordinates + "</geo>";
	    		documentController.insertXMLFragment(fragmentCoords, (AuthorNode) locationElement, AuthorConstants.POSITION_INSIDE_LAST);
	            
	            }
			} else {
				JOptionPane.showMessageDialog(null, "Suche nicht erfolgreich.");
				
			}

		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	// Method to get the index of a search result based on its Wikidata ID
	private static int getIndexByWikidataId(JSONArray searchResults, String wikidataId) {
		for (int i = 0; i < searchResults.length(); i++) {
			JSONObject result = searchResults.getJSONObject(i);
			if (result.optString("id").equals(wikidataId)) {
				return i;
			}
		}
		return -1; // ID not found
	}
	
	// Method to fetch selected item data using the Wikidata ID
	private static String fetchCoordinates(String selectedId) throws Exception {
	    String apiUrl = "https://www.wikidata.org/w/api.php" +
	            "?action=wbgetclaims" +
	            "&format=json" +
	            "&entity=" + selectedId +
	            "&property=P625"; // Property P625 represents coordinates

	    HttpClient httpClient = HttpClients.createDefault();
	    HttpGet httpGet = new HttpGet(apiUrl);

	    String responseBody = EntityUtils.toString(httpClient.execute(httpGet).getEntity());

	    JSONObject data = new JSONObject(responseBody);
	    JSONObject claims = data.optJSONObject("claims");
	    if (claims.has("P625")) {
	        JSONArray coordinateClaims = claims.getJSONArray("P625");
	        JSONObject coordinateClaim = coordinateClaims.getJSONObject(0); // Assuming there's only one claim

	        JSONObject mainSnak = coordinateClaim.optJSONObject("mainsnak");
	        if (mainSnak != null && "value".equals(mainSnak.optString("snaktype"))) {
	            JSONObject coordinateValue = mainSnak.getJSONObject("datavalue").getJSONObject("value");

	            String latitude = coordinateValue.optString("latitude");
	            String longitude = coordinateValue.optString("longitude");

	            String coordinates = latitude + ", " + longitude;
	            return coordinates;
	        }
	    }

	    return null; // Coordinates not found or couldn't be parsed
	}

	public String getDescription() {
		// TODO Auto-generated method stub
		return null;
	}

	public ArgumentDescriptor[] getArguments() {
		return null;
	}

}
