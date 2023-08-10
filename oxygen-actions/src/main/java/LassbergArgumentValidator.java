import ro.sync.ecss.extensions.api.ArgumentsMap;
import ro.sync.ecss.extensions.api.AuthorOperationException;

public class LassbergArgumentValidator {


	/**
	 * Based on https://github.com/ediarum/ediarum.JAR/blob/master/src/org/bbaw/telota/ediarum/extensions/EdiarumArgumentValidator.java
	 */


	    /**
	     * Validate parameter and get the user input as a string.
	     * @param argument
	     * @param args
	     * @return String value of the argument
	     * @throws AuthorOperationException
	     */
	    public static String validateStringArgument(String argument, ArgumentsMap args) throws AuthorOperationException
	    {
	        // Get the argument value
	        Object argumentValue = args.getArgumentValue(argument);

	        // Test if argument value is a string
	        if (argumentValue == null || ! (argumentValue instanceof String))
	        {
	            throw new IllegalArgumentException(
	                    "Das folgende Argument wurde nicht gesetzt" +
	                            argument + ": " + argumentValue
	            );
	        }

	        // return Value if valid
	        return (String) argumentValue;

	    }


	    /**
	     * Validate parameter and get the user input as a
	     * @param argument
	     * @param args
	     * @param defaultValue
	     * @return String value or default value of the argument
	     * @throws AuthorOperationException
	     */
	    public static String validateStringArgument(String argument, ArgumentsMap args, String defaultValue) throws AuthorOperationException
	    {

	        // Get the argument value
	        Object argumentValue = args.getArgumentValue(argument);

	        // Test if argument is a string and not null
	        if (argumentValue != null && argumentValue instanceof String)
	        {
	            return (String) argumentValue;
	        }

	        else if (!(argumentValue instanceof String))
	        {
	            throw new IllegalArgumentException(
	                    "Das folgende Argument wurde nicht korrekt gesetzt: " +
	                            argument + ": " + argumentValue
	            );
	        }

	        return defaultValue;

	    }

	

}