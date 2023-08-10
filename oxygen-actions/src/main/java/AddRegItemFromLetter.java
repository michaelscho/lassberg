import ro.sync.ecss.dom.wrappers.AuthorNodeList;
import ro.sync.ecss.extensions.api.ArgumentDescriptor;
import ro.sync.ecss.extensions.api.ArgumentsMap;
import ro.sync.ecss.extensions.api.AuthorAccess;
import ro.sync.ecss.extensions.api.AuthorConstants;
import ro.sync.ecss.extensions.api.AuthorDocumentController;
import ro.sync.ecss.extensions.api.AuthorOperation;
import ro.sync.ecss.extensions.api.AuthorOperationException;
import ro.sync.ecss.extensions.api.access.AuthorEditorAccess;
import ro.sync.ecss.extensions.api.access.AuthorWorkspaceAccess;
import ro.sync.ecss.extensions.api.node.AttrValue;
import ro.sync.ecss.extensions.api.node.AuthorElement;
import ro.sync.ecss.extensions.api.node.AuthorNode;
import ro.sync.exml.workspace.api.editor.WSEditor;
import ro.sync.exml.workspace.api.editor.page.author.WSAuthorEditorPage;

import java.awt.Frame;
import java.io.File;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import javax.swing.text.BadLocationException;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

public class AddRegItemFromLetter implements AuthorOperation {

	// Arguments passed from OxygenXML action tab
	private static final String REGISTER_FILE = "Path to register file";
	private static final String ROOT_ELEMENT = "Root element the item will be added to (such as 'personList', 'placeList' as string)";
	private static final String SUB_ELEMENT = "Subelement to be queried (such as 'person', 'place' or 'bibl' as string)";
	private static final String ID_BASE = "Base of ID such as 'lassberg-correspondent-' as string";
	private static final String ID_FULL_BASE = "relative path to register file such as '../register/lassberg-persons.xml' as string";

	// validation of arguments passed from OxygenXML action tab
	private static final ArgumentDescriptor[] ARGUMENTS = new ArgumentDescriptor[] {
			new ArgumentDescriptor(REGISTER_FILE, ArgumentDescriptor.TYPE_STRING, "Path to register file."),
			new ArgumentDescriptor(ROOT_ELEMENT, ArgumentDescriptor.TYPE_STRING, "Root element the item will be added to (such as 'personList', 'placeList' as string)."),
			new ArgumentDescriptor(SUB_ELEMENT, ArgumentDescriptor.TYPE_STRING, "Wrong element."),
			new ArgumentDescriptor(ID_BASE, ArgumentDescriptor.TYPE_STRING, "Base of ID such as 'lassberg-correspondent-' as string"),
			new ArgumentDescriptor(ID_FULL_BASE, ArgumentDescriptor.TYPE_STRING, "relative path to register file such as '../register/lassberg-persons.xml' as string"),


	};

	public void doOperation(AuthorAccess authorAccess, ArgumentsMap args)
			throws IllegalArgumentException, AuthorOperationException {

		// Initializing variables for arguments passed from OxygenXML action tab or css
		// oxy_button
		String pathToRegisterFile = LassbergArgumentValidator.validateStringArgument(REGISTER_FILE, args);
		String elementToBeQueried = LassbergArgumentValidator.validateStringArgument(ROOT_ELEMENT, args);
		String subElementToBeQueried = LassbergArgumentValidator.validateStringArgument(SUB_ELEMENT, args);
		String idBase = LassbergArgumentValidator.validateStringArgument(ID_BASE, args);
		String relativePathToID = LassbergArgumentValidator.validateStringArgument(ID_FULL_BASE, args);



		// initialize document controller
		AuthorDocumentController documentController = authorAccess.getDocumentController();
		// initialize editor controller
        AuthorWorkspaceAccess workspaceAccess = authorAccess.getWorkspaceAccess();
        

		// get current element
		AuthorNode currentElement =  documentController.findNodesByXPath(".", false, false, false)[0];
		
		//get Text
		String currentElementText = null;
		try {
			currentElementText = currentElement.getTextContent();
		} catch (BadLocationException e1) {
			// TODO Auto-generated catch block
			e1.printStackTrace();
		}
		
		// open file in oxygen
       
		try {
	        // Convert the path to a URL
	        URL fileURL = new URL("file:" + pathToRegisterFile);

	        // Open file or switch tab.
	        workspaceAccess.open(fileURL);

	        // get access to the opened register
	        WSEditor editorForRegisterFile = workspaceAccess.getEditorAccess(fileURL);
	        WSAuthorEditorPage authorEditorPageForRegisterFile = (WSAuthorEditorPage) editorForRegisterFile.getCurrentPage();
	        AuthorDocumentController documentControllerForRegisterFile = authorEditorPageForRegisterFile.getDocumentController();

	        String xmlFragment = null;
	        String xmlID = null;
	        
	        AuthorNode[] existingElements = documentControllerForRegisterFile.findNodesByXPath("//" + subElementToBeQueried, false, false, false);
	        int idNumber = existingElements.length + 1;
	        xmlID = idBase + String.format("%04d", idNumber);
	        
	        if (elementToBeQueried.equals("listPerson")) {
	        
	        xmlFragment = "<person xml:id=\"" + xmlID + "\" gender=\"\" ref=\"\" xmlns=\"http://www.tei-c.org/ns/1.0\">\n<persName type=\"main\">" + currentElementText 
	        		+ "</persName>\n<occupation></occupation>\n<birth when=\"\"></birth>\n<education></education>\n"
	        		+ "<ref target=\"\"></ref>\n</person>";
	        } 
	        if (elementToBeQueried.equals("listPlace")) {
		        
	        
	        xmlFragment = "<place xml:id=\"" + xmlID + "\" xmlns=\"http://www.tei-c.org/ns/1.0\">\n"
	        			+ "    <placeName ref=\"\">" + currentElementText + "</placeName>\n"
	        			+ "    <location>\n"
	        			+ "        <geo ana=\"wgs84\"></geo>\n"
	        			+ "    </location>\n"
	        			+ "</place>\\n";
	        }
	        
	        if (elementToBeQueried.equals("listBibl")) {
		        
		        
	        xmlFragment = "<bibl xml:id=\"" + xmlID + "\" xmlns=\"http://www.tei-c.org/ns/1.0\">\n"
	        			+ "	   <title>" + currentElementText +"</title>"
	        			+ "	   <idno type=\"\"></idno>"
	        			+ "</bibl>";
	        
	        }
	        
	        AuthorNode rootElement = documentControllerForRegisterFile.findNodesByXPath("//" + elementToBeQueried, false, false, false)[0];
	        
	        documentControllerForRegisterFile.insertXMLFragment(xmlFragment, rootElement, AuthorConstants.POSITION_INSIDE_LAST); 
	        
	        // ad or replace ID in letter
			documentController.setAttribute("key", new AttrValue(relativePathToID + "#" + xmlID), (AuthorElement) currentElement);

	        
	    } catch (Exception e) {
	        throw new AuthorOperationException("Failed to open or switch to file: " + e.getMessage(), e);
	    }
	}
        

	public String getDescription() {
		// TODO Auto-generated method stub
		return null;
	}

	public ArgumentDescriptor[] getArguments() {
		return ARGUMENTS;
	}
}