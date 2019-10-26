"""
This is used to check value is verified and returned
"""
import re
from Libs.Exception.CustomExceptions import InvalidParamException

# Size units
BYTE='B'
KILOBYTE='KB'
MEGABYTE='MB'
GIGABYTE='GB'
TERABYTE='TB'
PETABYTE='PB'
BLOCK='BC'
PERCENT='%'
SIZE_UNITS = [BLOCK, BYTE, KILOBYTE, MEGABYTE, GIGABYTE, PETABYTE]

# Time units
MICROSECOND='US'
MILLISECOND='MS'
SECOND='S'
MINUTE='M'
HOUR='H'
DAY='D'
WEEK='WK'
MONTH='MO'
YEAR='YR'
TIME_UNITS=[MICROSECOND, MILLISECOND, SECOND, MINUTE, HOUR, DAY, WEEK, MONTH, YEAR]

# Represents any values, including scientific notation like 2E+4 etc
NUMBER_REGEX = "^[+-]?(((\d+(\.\d*)?)|0\.\d+)([eE][+-]?[0-9]+)?)"

# Regex for percentage, time and size
PERCENTAGE_REGEX = '\d+(\.\d+)?%$'
TIME_REGEX = NUMBER_REGEX + "(" + "|".join(TIME_UNITS) + ")$"
SIZE_REGEX = NUMBER_REGEX + "(" + "|".join(SIZE_UNITS) + ")$"
TIME_UNIT_REGEX = "^(" + "|".join(TIME_UNITS) + ")$"
SIZE_UNIT_REGEX = "^(" + "|".join(SIZE_UNITS) + ")$"

# Size unit conversion, based on B
ONE_K = 1024
ONE_BC = 512
ONE_MB = float(ONE_K*ONE_K)
ONE_GB = float(ONE_MB*ONE_K)
ONE_TB = float(ONE_GB*ONE_K)
ONE_PB = float(ONE_TB*ONE_K)

# Time units conversion, based on S
ONE_US = float(1/float(1000000))
ONE_MS = float(1/float(1000))
ONE_M = 60
ONE_H = 60 * ONE_M
ONE_D = 24 * ONE_H
ONE_WK = 7 * ONE_D
ONE_MO = 30 * ONE_D
ONE_YR = float(365 * ONE_D)

class Units:
    """
    Units class
    Function Description : It is used to check whether Size, Time and Number
    match the format and get the value of Size, Number and Time

    Args:
        None

    Note:
          This class is only used to check the format of size, time object not else where
    """
    def __init__(self):
        pass

    @classmethod
    def isPercentage(cls, value):
        """
        Determine if percentage is legal

        Args:
             Value (str) :: Any string or number

        Returns:
              True (bool) :: if percentage is legal
              False (bool) :: if percentage is not legal/valid

        Example:
              Units.isPercentage('10%')
        """
        return re.match(PERCENTAGE_REGEX, value) is not None

    @classmethod
    def isTime(cls, value):
        """
        Determine if time is legal

        Args:
             Value (str) :: Any string or number

        Returns:
              True (bool) :: if time is legal
              False (bool) :: if time is not legal/valid

        Example:
              Units.isTime('10S')
        """
        return re.match(r'' + str(TIME_REGEX) + '', str(value), re.IGNORECASE) is not None

    @classmethod
    def isSize(cls, value):
        """
        Determine if size is legal

        Args:
             Value (str) :: Any string or number

        Returns:
              True (bool) :: if time is legal
              False (bool) :: if time is not legal/valid

        Note:
            The correct format is a combination of values and SIZE_UNITS

        Example:
              Units.isTime('10TB')
        """
        return re.match(r'' + str(SIZE_REGEX) + '', str(value), re.IGNORECASE) is not None

    @classmethod
    def isNumber(cls, value):
        """
        Determine if number is legal(int, float, double etc)

        Args:
             Value (str|int|float|long) :: Any string or number

        Returns:
              True (bool) :: if number is legal
              False (bool) :: if number is not legal/valid

        Example:
              Units.isTime('3E10')
        """
        numberFlag = False
        if isinstance(value, str):
            if re.match(r'^' + str(NUMBER_REGEX) + '$', value):
                numberFlag = True
            else:
                numberFlag = False
        return isinstance(value, int) or isinstance(value, float) or isinstance(value, long) or numberFlag

    @staticmethod
    def isUnsignedNumeric(value):
        """
        Determine if number is positive(int, float, double etc)

        Args:
             Value (str|int|float|long) :: Any string or number

        Returns:
              True (bool) :: if number is positive
              False (bool) :: if number is not positive
        """
        try:
            int(value)
        except:
            return False
        if int(value) >= 0:
            return True

    @classmethod
    def getNumber(cls, value):
        """
        Get the value with the unit parameter

        This function is used to obtain the value of a parameter of a numeric
        type or a parameter type of time and size

        Args:
             Value (str|int|float|long) :: Any string or number

        Returns:
            Values (int) :: value after removing the unit

        Raises:
              InvalidParamException, when input value is illegal

        Example:
              Units.getNumber('100GB')
        """
        if value is None:
            return None

        if Units.isNumber(value):
            return float(value)

        if Units.isTime(value) or Units.isSize(value) or Units.isPercentage(value):
            values = float(re.sub(r'[a-zA-Z%]*$', '', str(value)))
            return values
        raise InvalidParamException('getNumber() failed, Input value(%s) is invalid'%(value))

    @classmethod
    def getUnit(cls, value):
        """
         Get the unit with unit parameters

         This function is used to get the unit of the numeric type or parameter
         whose parameter type is time and size

         Args:
             value (str|int|float|long) :: Any string or number

         Returns:
               Unit (str) :: The unit of value

         Raises:
              InvalidParamException, when input value is illegal

        Example:
              Units.getUnit('100GB')
        """
        if Units.isTime(value) or Units.isSize(value):
            unit = re.sub(r'' + str(NUMBER_REGEX) + '', "", value)
            return unit
        raise InvalidParamException("getUnit failed, input value(%s) is not size or time type"%(value))

    @classmethod
    def convert(cls, value, unit):
        """
        Convert the specified value to the value of specified unit

        Args:
            unit  (str) :: The target unit of the conversion
            value (str) :: Any string with size

        Returns:
              value (str) :: the converted string

        Example:
              Units.convert('10GB', 'MB')
        """
        if Units.isTime(value) and re.match(r'' + str(TIME_UNIT_REGEX) + '',
                                            str(unit),
                                            re.IGNORECASE):
            rate = Units._rate(Units.getUnit(value), unit)
            return str(rate * Units.getNumber(value)) + unit.upper()

    @staticmethod
    def _rate(fromUnit, toUnit):
        """
        Calculate the ratio of conversion from fromUnit to toUnit

        Args:
             fromUnit (str) :: the source unit of the conversion
             toUnit   (str) :: the target unit of the conversion

        Returns:
              rate (float) :: the ratio of the conversion from source unit to target unit

        Raises:
              InvalidParamException, when argument passed is incorrect

        Examples:
              rate = Units._rate("GB", "MB")
        """
        if not isinstance(fromUnit, str) and not isinstance(toUnit, str):
            raise InvalidParamException('convert units failed, parameter failed')
        fromUnit = fromUnit.upper()
        toUnit = toUnit.upper()

        # the benchmark ratio dictionary for the size type
        sizeBaseRate = {BYTE: 1,
                        BLOCK: ONE_BC,
                        KILOBYTE: ONE_K,
                        MEGABYTE: ONE_MB,
                        GIGABYTE: ONE_GB,
                        TERABYTE: ONE_TB,
                        PETABYTE: ONE_PB}
        # the benchmark ratio dictionary for the time type
        timeBaseRate = {MICROSECOND: ONE_US,
                        MILLISECOND: ONE_MS,
                        SECOND: 1,
                        MINUTE: ONE_M,
                        HOUR: ONE_H,
                        DAY: ONE_D,
                        WEEK: ONE_WK,
                        MONTH: ONE_MO,
                        YEAR: ONE_YR}

        # If the incoming one are of type time
        if re.match(r'' + str(TIME_UNIT_REGEX) + '', str(fromUnit), re.IGNORECASE) and re.match(r'' + str(TIME_UNIT_REGEX) + '', str(toUnit), re.IGNORECASE):
            fromUnitRate = timeBaseRate.get(fromUnit, 0)
            toUnitRate = timeBaseRate.get(toUnit, 0)
            return float(float(fromUnitRate)/float(toUnitRate))
        # If the incoming are both size type
        elif re.match(r'' + str(SIZE_UNIT_REGEX) + '', str(fromUnit), re.IGNORECASE) and re.match(r'' + str(SIZE_UNIT_REGEX) + '', str(toUnit), re.IGNORECASE):
            fromUnitRate = sizeBaseRate.get(fromUnit, 0)
            toUnitRate = sizeBaseRate.get(toUnit, 0)
            return float(float(fromUnitRate)/float(toUnitRate))
        else:
            raise InvalidParamException("%s and %s is not same type."%(fromUnit, toUnit))

    @classmethod
    def substract(cls, maxValue, minValue):
        """
        calculate the difference between two unit values

        Args:
             maxValue (str) :: A string of type Time and Size, with a value greater than minValue
             minValue (str) :: A string of type Time and Size, with a value less than minValue

        Returns:
              substract (str) :: the time and size strings after substraction

        Example:
              Units.substract('10GB', '2GB')
              output :: '8GB'
        """
        numMaxValue, numMinValue, unit = Units._baseMath(maxValue, minValue)
        total = numMaxValue - numMinValue
        return str(total) + unit

    @classmethod
    def _baseMath(cls, valueA, valueB):
        """
        Calculate the values and units of two units with unit data

        Converts the values of the two valuesbased on the minimum unit of the two data
        and returns the calculated value and unit

        Args:
            valueA (str) :: A string of type Time and Size
            valueB (str) :: A string of type Time and Size

        Returns:
              numValueA (float) :: The converted valueA value.
              numValueB (float) :: converted valueB value
              unit (str) :: two minimum units with unit data

        Example:
              Units._baseMath('1GB', '200MB')
              output :: '1024', '200', 'MB'
        """
        numValueA, unitValueA = Units.parse(valueA)
        numValueB, unitValueB = Units.parse(valueB)

        if unitValueB == unitValueA:
            return numValueA, numValueB, unitValueA
        else:
            unit = Units.getSmallerUnit(unitValueA, unitValueB)
            numValueA = Units.getNumber(Units.convert(valueA, unit))
            numValueB = Units.getNumber(Units.convert(valueB, unit))
            return numValueA, numValueB, unit

    @classmethod
    def getSmallerUnit(cls, unitA, unitB):
        """
        Get the smallest unit of two units

        Args:
             unitA (str) :: unit string of type Time and Size
             unitB (str) :: unit string of type Time and Size

        Returns:
              unit (str) :: the smallest unit of two units

        Example:
              Units.getSmallerUnit('1GB', '200MB')
              output :: 'MB'
        """
        if unitA == unitB:
            return unitA
        elif unitA in SIZE_UNITS and unitB in SIZE_UNITS:
            for unit in SIZE_UNITS:
                if unit == unitA:
                    return unitA
                elif unit == unitB:
                    return unitB
        elif unitB in TIME_UNITS and unitB in TIME_UNITS:
            for unit in TIME_UNITS:
                if unit == unitA:
                    return unitA
                elif unit == unitB:
                    return unitB
        elif unitA == PERCENT and unitB == PERCENT:
            return PERCENT
        else:
            raise InvalidParamException('The provided units are not valid! %s and %s'%(unitB, unitA))

    @classmethod
    def getLargerUnit(cls, unitA, unitB):
        """
        Get the big unit of two units

        Args:
             unitA (str) :: unit string of type Time and Size
             unitB (str) :: unit string of type Time and Size

        Returns:
              unit (str) :: the largest unit of two units
        """
        if unitA == unitB:
            return unitA
        elif unitA in SIZE_UNITS and unitB in SIZE_UNITS:
            for unit in sorted(SIZE_UNITS, reverse=True):
                if unit == unitA:
                    return unitA
                elif unit == unitB:
                    return unitB
        elif unitB in TIME_UNITS and unitB in TIME_UNITS:
            for unit in sorted(TIME_UNITS, reverse=True):
                if unit == unitA:
                    return unitA
                elif unit == unitB:
                    return unitB
        else:
            raise InvalidParamException('The provided units are not valid! %s and %s'%(unitB, unitA))

    @classmethod
    def parse(cls, value):
        """
        Get the value and units with unit data

        Args:
            value (str) :: unit string of type Time and Size

        Returns:
              unit (str) :: unit of value data
              num (float) :: value of value data

        Example:
              Units.parse('1GB')
              output :: '1', 'GB'
        """
        err = "%s does not appear to be in units format"%(value)
        num, unit = None, None

        if not Units.isSize(value) and not Units.isTime(value) and not Units.isPercentage(value):
            raise InvalidParamException(err)
        matchUnit = re.match(r'' + str(NUMBER_REGEX) + '(\S+)', value)

        if matchUnit:
            num = float(matchUnit.group(1))
            unit = matchUnit.group(6)
        else:
            raise InvalidParamException(err)
        return num, unit

    @staticmethod
    def _compare(unitType, valueA, valueB):
        """
        Compare the size of two units

        Args:
             unitType (str) :: type of unit data
             valueA (str) :: unit string
             valueB (str) :: unit string

        Returns:
              cmpValue (float) :: the ratio of two data, if valueA is greater it returns positive
                                  if not then negative number

        Example:
              Units._compare('1GB', '1000MB')
              output :: 24
        """
        if re.match(r'percentage|size|time', unitType.lower()):
            numValueA, numValueB, unit = Units._baseMath(valueA, valueB)
            return numValueA - numValueB
        else:
            raise InvalidParamException("Type: %s is invalied"%(unitType))

    @classmethod
    def comparePercentage(cls, valueA, valueB):
        """
        Compare the size of two percentage type data

        Args:
             valueA (str) :: unit string of type percentage
             valueB (str) :: unit string of type percentage

        Returns:
              cmpValue (float) :: the ratio of two data, if valueA is greater it returns positive
                                  if not then negative number

        Example:
              Units._compare('1GB', '1000MB')
              output :: 24
        """
        if Units.isPercentage(valueA) and Units.isPercentage(valueB):
            return Units._compare('percentage', valueA, valueB)
        else:
            raise InvalidParamException("valueA or valueB is not size type")

    @classmethod
    def compareSize(cls, valueA, valueB):
        """
        Compare the size of two size type data

        Args:
             valueA (str) :: unit string of type size
             valueB (str) :: unit string of type size

        Returns:
              cmpValue (float) :: the ratio of two data, if valueA is greater it returns positive
                                  if not then negative number

        Example:
              Units._compare('1GB', '1000MB')
              output :: 24
        """
        if Units.isSize(valueA) and Units.isSize(valueB):
            return Units._compare('size', valueA, valueB)
        else:
            raise InvalidParamException("valueA or valueB is not size type")

    @classmethod
    def compareTime(cls, valueA, valueB):
        """
        Compare the size of two time type data

        Args:
             valueA (str) :: unit string of type time
             valueB (str) :: unit string of type time

        Returns:
              cmpValue (float) :: the ratio of two data, if valueA is greater it returns positive
                                  if not then negative number

        Example:
              Units.compareTime('1H', '70M')
              output :: 10
        """
        if Units.isTime(valueA) and Units.isTime(valueB):
            return Units._compare('time', valueA, valueB)
        else:
            raise InvalidParamException("valueA or valueB is not size type")

    @classmethod
    def add(cls, valueA, valueB):
        """
        Two unit data are summed according to the minimum unit

        Args:
             valueA (str) :: A unit string of type Time or Size
             valueB (str) :: A unit string of type Time or Size

        Returns:
              total (str) :: the sum of two data

        Example:
              Units.add('1H', '70M')
              output :: 130
        """
        numValueA, numValueB, unit = Units._baseMath(valueA, valueB)
        total = numValueA + numValueB

        return str(total) + unit

    @classmethod
    def divide(cls, valueA, number):
        """
        This method returns the unit value valueA divided by the unit value after the number

        Args:
             valueA (str) :: A unit string of type Time or Size
             number (int / float) :: divisor

        Returns:
              total (str) :: the unit value of valueA / number

        Example:
              Units.divide('1H', 2)
              output :: 0.5H
        """
        if isinstance(valueA, str) and (isinstance(number, int) or isinstance(number, float)):
            numValueA, unit = Units.parse(valueA)
            total = float(numValueA / number)
            return str(total) + unit
        else:
            raise InvalidParamException('Input invalid parameter %s(%s) %s(%s), should be str and int/float'%(valueA, type(valueA), number, type(number)))
