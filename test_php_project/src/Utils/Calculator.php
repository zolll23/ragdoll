<?php

namespace App\Utils;

/**
 * Calculator utility class
 * Demonstrates various complexity levels
 */
class Calculator
{
    /**
     * Simple addition - O(1)
     */
    public static function add(float $a, float $b): float
    {
        return $a + $b;
    }
    
    /**
     * Sum array - O(n)
     */
    public static function sum(array $numbers): float
    {
        $total = 0;
        foreach ($numbers as $number) {
            $total += $number;
        }
        return $total;
    }
    
    /**
     * Find duplicates - O(n^2)
     */
    public static function findDuplicates(array $array): array
    {
        $duplicates = [];
        $count = count($array);
        
        for ($i = 0; $i < $count; $i++) {
            for ($j = $i + 1; $j < $count; $j++) {
                if ($array[$i] === $array[$j]) {
                    $duplicates[] = $array[$i];
                }
            }
        }
        
        return array_unique($duplicates);
    }
    
    /**
     * Factorial - O(n) time, O(n) space (recursive)
     */
    public static function factorial(int $n): int
    {
        if ($n <= 1) {
            return 1;
        }
        
        return $n * self::factorial($n - 1);
    }
    
    /**
     * Binary search - O(log n)
     */
    public static function binarySearch(array $sortedArray, int $target): ?int
    {
        $left = 0;
        $right = count($sortedArray) - 1;
        
        while ($left <= $right) {
            $mid = (int)(($left + $right) / 2);
            
            if ($sortedArray[$mid] === $target) {
                return $mid;
            }
            
            if ($sortedArray[$mid] < $target) {
                $left = $mid + 1;
            } else {
                $right = $mid - 1;
            }
        }
        
        return null;
    }
    
    /**
     * Generate all permutations - O(n!)
     * WARNING: This method has factorial time complexity!
     * For n=10, this generates 3,628,800 permutations
     * 
     * @param array $items Items to permute
     * @return array All possible permutations
     */
    public static function generateAllPermutations(array $items): array
    {
        $n = count($items);
        
        // Base case: empty or single item
        if ($n <= 1) {
            return [$items];
        }
        
        $permutations = [];
        
        // Generate permutations recursively
        for ($i = 0; $i < $n; $i++) {
            // Remove current item
            $remaining = $items;
            $current = array_splice($remaining, $i, 1)[0];
            
            // Recursively generate permutations of remaining items
            $subPermutations = self::generateAllPermutations($remaining);
            
            // Prepend current item to each sub-permutation
            foreach ($subPermutations as $subPerm) {
                $permutations[] = array_merge([$current], $subPerm);
            }
        }
        
        return $permutations;
    }
    
    /**
     * Matrix multiplication - O(n³) but demonstrates nested loops
     * This is a clear example of O(n²) when matrices are square
     * 
     * @param array $matrixA First matrix (n x m)
     * @param array $matrixB Second matrix (m x p)
     * @return array Result matrix (n x p)
     */
    public static function multiplyMatrices(array $matrixA, array $matrixB): array
    {
        $rowsA = count($matrixA);
        $colsA = count($matrixA[0]);
        $colsB = count($matrixB[0]);
        
        $result = [];
        
        // O(n²) or O(n³) depending on matrix dimensions
        for ($i = 0; $i < $rowsA; $i++) {
            $result[$i] = [];
            for ($j = 0; $j < $colsB; $j++) {
                $sum = 0;
                for ($k = 0; $k < $colsA; $k++) {
                    $sum += $matrixA[$i][$k] * $matrixB[$k][$j];
                }
                $result[$i][$j] = $sum;
            }
        }
        
        return $result;
    }
    
    /**
     * Find all pairs with nested loops - O(n²)
     * Clear example of quadratic complexity
     * 
     * @param array $array Input array
     * @return array All pairs (i, j) where i < j
     */
    public static function findAllPairs(array $array): array
    {
        $pairs = [];
        $n = count($array);
        
        // Nested loops = O(n²)
        for ($i = 0; $i < $n; $i++) {
            for ($j = $i + 1; $j < $n; $j++) {
                $pairs[] = [$array[$i], $array[$j]];
            }
        }
        
        return $pairs;
    }
}


