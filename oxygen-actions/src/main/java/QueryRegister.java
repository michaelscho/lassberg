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

import java.awt.Frame;
import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

public class QueryRegister implements AuthorOperation {

	// Arguments passed from OxygenXML action tab
	private static final String REGISTER_FILE = "Path to register file";
	private static final String ROOT_ELEMENT = "Element to be queried (such as 'person', 'place' as string)";
	private static final String SUB_ELEMENT = "Subelement to be queried (such as 'persName', 'placeName' or 'bibl' as string)";

	// validation of arguments passed from OxygenXML action tab
	private static final ArgumentDescriptor[] ARGUMENTS = new ArgumentDescriptor[] {
			new ArgumentDescriptor(REGISTER_FILE, ArgumentDescriptor.TYPE_STRING, "Path to register file."),
			new ArgumentDescriptor(ROOT_ELEMENT, ArgumentDescriptor.TYPE_STRING, "Element to be queried (such as 'person', 'place' as string)."),
			new ArgumentDescriptor(SUB_ELEMENT, ArgumentDescriptor.TYPE_STRING, "Wrong element."),};

	public void doOperation(AuthorAccess authorAccess, ArgumentsMap args)
			throws IllegalArgumentException, AuthorOperationException {

		// Initializing variables for arguments passed from OxygenXML action tab or css
		// oxy_button
		String pathToRegisterFile = LassbergArgumentValidator.validateStringArgument(REGISTER_FILE, args);
		String elementToBeQueried = LassbergArgumentValidator.validateStringArgument(ROOT_ELEMENT, args);
		String subElementToBeQueried = LassbergArgumentValidator.validateStringArgument(SUB_ELEMENT, args);

		

		// initialize sortable ArrayList with entries taken from register
		List<String> listOfEntries = new ArrayList<String>();

		try {
			// Parse the XML file
			File file = new File(pathToRegisterFile);
			DocumentBuilderFactory documentBuilderFactory = DocumentBuilderFactory.newInstance();
			DocumentBuilder documentBuilder = documentBuilderFactory.newDocumentBuilder();
			Document document = documentBuilder.parse(file);
			document.getDocumentElement().normalize();

			String namespaceURI = "http://www.tei-c.org/ns/1.0";
			
			// Get elements
            NodeList nodeList = document.getElementsByTagName(elementToBeQueried);

			for (int i = 0; i < nodeList.getLength(); i++) {
				Node node = nodeList.item(i);

				String entry = "";
				String displayedText;

				if (node.getNodeType() == Node.ELEMENT_NODE) {
					Element element = (Element) node;
					// get xml:id
					String xmlID = element.getAttribute("xml:id");
					if (elementToBeQueried.contains("bibl")) {
						displayedText = element.getTextContent();
					} else {
						displayedText = element.getElementsByTagName(subElementToBeQueried).item(0).getTextContent();
					}

					
					entry = displayedText + "##" + xmlID;

					listOfEntries.add(entry);

				} 
			}
		} catch (Exception e) {
			e.printStackTrace();
			throw new AuthorOperationException("Error while reading XML file: " + e.getMessage(), e);
		}
		
		Collections.sort(listOfEntries);
		List<String> listOfEntriesCopy = new ArrayList<String>();
		for (int i=0; i < listOfEntries.size(); i++) {
			String entry = listOfEntries.get(i);
			entry = entry.split("##")[0];
			listOfEntriesCopy.add(entry);
		}

		String[] listOfEntriesForDialog = listOfEntriesCopy.toArray(new String[0]);

		// Pass data to selection dialog
		OpenDialog register = new OpenDialog((Frame) authorAccess.getWorkspaceAccess().getParentFrame(),
				listOfEntriesForDialog, "Eintrag auswählen", true);
		
		// Create attribute string
		String indexString = register.getSelectedID();
		String correspondingItem = "";
		for(int i=0;i<listOfEntries.size();i++)
			{
			if (listOfEntries.get(i).startsWith(indexString))
			    {
					correspondingItem = listOfEntries.get(i).split("##")[1];
			    }
			}
								
		AuthorDocumentController documentController = authorAccess.getDocumentController();

		AuthorNode[] currentElement = documentController.findNodesByXPath(".", false, false, false);
		// update key=""
		documentController.setAttribute("key", new AttrValue(correspondingItem), (AuthorElement) currentElement[0]);
	}

	public String getDescription() {
		// TODO Auto-generated method stub
		return null;
	}

	public ArgumentDescriptor[] getArguments() {
		return ARGUMENTS;
	}
}